import argparse
import time

import torch.nn.parallel
import torch.optim
# from sklearn.metrics import confusion_matrix
from ops.dataset import TSNDataSet
from src.model_fc import TSN
from ops.transforms import *
from ops import dataset_config
from torch.nn import functional as F
import os
os.environ["CUDA_VISIBLE_DEVICES"] = '1,2'

# options
parser = argparse.ArgumentParser(description="TSM testing on the full validation set")
parser.add_argument('dataset', type=str)

# may contain splits
parser.add_argument('--weights', type=str, default=None)
parser.add_argument('--test_segments', type=str, default=25)
parser.add_argument('--dense_sample', default=False, action="store_true", help='use dense sample as I3D')
parser.add_argument('--twice_sample', default=False, action="store_true", help='use twice sample for ensemble')
parser.add_argument('--full_res', default=False, action="store_true",
                    help='use full resolution 256x256 for test as in Non-local I3D')

parser.add_argument('--test_crops', type=int, default=1)
parser.add_argument('--coeff', type=str, default=None)
parser.add_argument('--batch_size', type=int, default=1)
parser.add_argument('-j', '--workers', default=1, type=int, metavar='N',
                    help='number of data loading workers (default: 8)')

# for true test
parser.add_argument('--test_list', type=str, default=None)
parser.add_argument('--csv_file', type=str, default=None)

parser.add_argument('--softmax', default=False, action="store_true", help='use softmax')

parser.add_argument('--max_num', type=int, default=-1)
parser.add_argument('--input_size', type=int, default=224)
parser.add_argument('--crop_fusion_type', type=str, default='avg')
parser.add_argument('--img_feature_dim',type=int, default=256)
parser.add_argument('--num_set_segments',type=int, default=1,help='TODO: select multiply set of n-frames from a video')
parser.add_argument('--pretrain', type=str, default='imagenet')

args = parser.parse_args()


class AverageMeter(object):
    """Computes and stores the average and current value"""
    def __init__(self):
        self.reset()

    def reset(self):
        self.val = 0
        self.avg = 0
        self.sum = 0
        self.count = 0

    def update(self, val, n=1):
        self.val = val
        self.sum += val * n
        self.count += n
        self.avg = self.sum / self.count


def accuracy(output, target, topk=(1,)):
    """Computes the precision@k for the specified values of k"""
    maxk = max(topk)
    batch_size = target.size(0)
    _, pred = output.topk(maxk, 1, True, True)
    pred = pred.t()
    correct = pred.eq(target.view(1, -1).expand_as(pred))
    res = []
    for k in topk:
         correct_k = correct[:k].view(-1).float().sum(0)
         res.append(correct_k.mul_(100.0 / batch_size))
    return res


weights_list = args.weights.split(',')
test_segments_list = [int(s) for s in args.test_segments.split(',')]
assert len(weights_list) == len(test_segments_list)
if args.coeff is None:
    coeff_list = [1] * len(weights_list)
else:
    coeff_list = [float(c) for c in args.coeff.split(',')]

if args.test_list is not None:
    test_file_list = args.test_list.split(',')
else:
    test_file_list = [None] * len(weights_list)


data_iter_list = []
net_list = []
modality_list = []

total_num = None
for this_weights, this_test_segments, test_file in zip(weights_list, test_segments_list, test_file_list):
    this_arch = this_weights.split('FC_')[1].split('_')[2]
    modality = 'HP'
    data_length = 3
    modality_list.append(modality)
    num_class, args.train_list, val_list, root_path, prefix = dataset_config.return_dataset(args.dataset, modality)
    net = TSN(num_class, this_test_segments, data_length, this_arch, modality=modality)

    input_size = net.scale_size if args.full_res else net.input_size
    if args.test_crops == 1:
        cropping = torchvision.transforms.Compose([
            GroupScale(net.scale_size),
            GroupCenterCrop(input_size),
        ])
    elif args.test_crops == 3:  # do not flip, so only 5 crops
        cropping = torchvision.transforms.Compose([
            GroupFullResSample(input_size, net.scale_size, flip=False)
        ])
    elif args.test_crops == 5:  # do not flip, so only 5 crops
        cropping = torchvision.transforms.Compose([
            GroupOverSample(input_size, net.scale_size, flip=False)
        ])
    elif args.test_crops == 10:
        cropping = torchvision.transforms.Compose([
            GroupOverSample(input_size, net.scale_size)
        ])
    else:
        raise ValueError("Only 1, 5, 10 crops are supported while we got {}".format(args.test_crops))

    data_loader = torch.utils.data.DataLoader(
            TSNDataSet(args.dataset, root_path, test_file if test_file is not None else val_list, num_segments=this_test_segments,
                       data_length=data_length,
                       modality=modality,
                       image_tmpl=prefix,
                       test_mode=True,
                       remove_missing=len(weights_list) == 1,
                       transform=torchvision.transforms.Compose([
                           cropping,
                           Stack(roll=False),
                           ToTorchFormatTensor(div=True),
                           GroupNormalize(net.input_mean, net.input_std),
                       ]), dense_sample=args.dense_sample, twice_sample=args.twice_sample),
            batch_size=args.batch_size, shuffle=False,
            num_workers=args.workers, pin_memory=True,
    )
    
    net = torch.nn.DataParallel(net.cuda())
    checkpoint = torch.load(this_weights)
    e_ = checkpoint['epoch']
    print("=> loaded checkpoint, (epoch {})".format(e_))
    net.load_state_dict(checkpoint['state_dict'])

#     net = torch.nn.DataParallel(net.cuda())
    net.eval()

    data_gen = enumerate(data_loader)

    if total_num is None:
        total_num = len(data_loader.dataset)
    else:
        assert total_num == len(data_loader.dataset)

    data_iter_list.append(data_gen)
    net_list.append(net)


output = []


def eval_video(video_data, net, this_test_segments, modality):
    net.eval()
    with torch.no_grad():
        i, data, label = video_data
        batch_size = label.numel()
        num_crop = args.test_crops
        if args.dense_sample:
            num_crop *= 10  # 10 clips for testing when using dense sample

        if args.twice_sample:
            num_crop *= 2

        if modality == 'RGB' or modality == 'HP':
            length = 3
        elif modality == 'Flow':
            length = 10
        elif modality == 'RGBDiff':
            length = 18
        else:
            raise ValueError("Unknown modality "+ modality)
        #nt3, c, h, w
        data_in = data.view(-1, length, data.size(-2), data.size(-1))
        rst = net(data_in)
        rst = rst.reshape(batch_size, num_crop, -1).mean(1) #n, num_classes

        if args.softmax:
            # take the softmax to normalize the output to probability
            rst = F.softmax(rst, dim=1)

        rst = rst.data.cpu().numpy().copy()

#         rst = rst.reshape(batch_size, num_class)


        return i, rst, label


proc_start_time = time.time()
max_num = args.max_num if args.max_num > 0 else total_num

top1 = AverageMeter()
top5 = AverageMeter()

for i, data_label_pairs in enumerate(zip(*data_iter_list)):
    with torch.no_grad():
        if i >= max_num:
            break
        this_rst_list = []
        this_label = None
        for n_seg, (_, (data, label)), net, modality in zip(test_segments_list, data_label_pairs, net_list, modality_list):
            rst = eval_video((i, data, label), net, n_seg, modality)
            this_rst_list.append(rst[1])
            this_label = label
        assert len(this_rst_list) == len(coeff_list)
        for i_coeff in range(len(this_rst_list)):
            this_rst_list[i_coeff] *= coeff_list[i_coeff]
        ensembled_predict = sum(this_rst_list) / len(this_rst_list)

        for p, g in zip(ensembled_predict, this_label.cpu().numpy()):
            output.append([p[None, ...], g])
        cnt_time = time.time() - proc_start_time
        prec1, prec5 = accuracy(torch.from_numpy(ensembled_predict), this_label, topk=(1, 5))
        top1.update(prec1.item(), this_label.numel())
        top5.update(prec5.item(), this_label.numel())
        if i % 20 == 0:
            print('video {} done, total {}/{}, average {:.3f} sec/video, '
                  'moving Prec@1 {:.3f} Prec@5 {:.3f}'.format(i * args.batch_size, i * args.batch_size, total_num,
                                                              float(cnt_time) / (i+1) / args.batch_size, top1.avg, top5.avg))

video_pred = [np.argmax(x[0]) for x in output]
video_pred_top5 = [np.argsort(np.mean(x[0], axis=0).reshape(-1))[::-1][:5] for x in output]

video_labels = [x[1] for x in output]


if args.csv_file is not None:
    print('=> Writing result to csv file: {}'.format(args.csv_file))
    with open(test_file_list[0].replace('test_videofolder.txt', 'category.txt')) as f:
        categories = f.readlines()
    categories = [f.strip() for f in categories]
    with open(test_file_list[0]) as f:
        vid_names = f.readlines()
    vid_names = [n.split(' ')[0] for n in vid_names]
    assert len(vid_names) == len(video_pred)
    if args.dataset != 'somethingv2':  # only output top1
        with open(args.csv_file, 'w') as f:
            for n, pred in zip(vid_names, video_pred):
                f.write('{};{}\n'.format(n, categories[pred]))
    else:
        with open(args.csv_file, 'w') as f:
            for n, pred5 in zip(vid_names, video_pred_top5):
                fill = [n]
                for p in list(pred5):
                    fill.append(p)
                f.write('{};{};{};{};{};{}\n'.format(*fill))


# cf = confusion_matrix(video_labels, video_pred).astype(float)

# np.save('cm.npy', cf)
# cls_cnt = cf.sum(axis=1)
# cls_hit = np.diag(cf)

# cls_acc = cls_hit / cls_cnt
# print(cls_acc)
# upper = np.mean(np.max(cf, axis=1) / cls_cnt)
# print('upper bound: {}'.format(upper))

print('-----Evaluation is finished------')
# print('Class Accuracy {:.02f}%'.format(np.mean(cls_acc) * 100))
print('Overall Prec@1 {:.02f}% Prec@5 {:.02f}%'.format(top1.avg, top5.avg))