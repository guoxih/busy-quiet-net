# import torch.utils.data as data

# from PIL import Image
# import os
# import numpy as np
# import csv
# from numpy.random import randint


# class VideoRecord(object):
#     def __init__(self, row, data_length):
#         self._data = row
#         self._data_length = data_length

#     @property
#     def path(self):
#         return self._data[0]

#     @property
#     def num_frames(self):
# #         return int(self._data[1]) - self._data_length + 1
#         return int(self._data[1])

#     @property
#     def label(self):
#         return int(self._data[2])

# class UCF101VideoRecord(object):
#     def __init__(self, row, data_length):
#         self._data = row
#         self._data_length = data_length

#     @property
#     def path(self):
#         return self._data[2]

#     @property
#     def num_frames(self):
#         _len = int(self._data[3])
# #         return _len - self._data_length + 1
#         return _len
 
#     @property
#     def label(self):
#         return int(self._data[1])
    
# class TSNDataSet(data.Dataset):
#     def __init__(self, dataset, root_path, list_file,
#                  num_segments=3, data_length=1, modality='RGB',
#                  image_tmpl='img_{:05d}.jpg', transform=None,
#                  random_shift=True, test_mode=False,
#                  remove_missing=False, dense_sample=False, twice_sample=False):
#         self.root_path = root_path
#         self.list_file = list_file
#         self.num_segments = num_segments
#         self.data_length = data_length
#         self.modality = modality
#         self.image_tmpl = image_tmpl
#         self.transform = transform
#         self.random_shift = random_shift
#         self.test_mode = test_mode
#         self.remove_missing = remove_missing
#         self.dense_sample = dense_sample  # using dense sample as I3D
#         self.twice_sample = twice_sample  # twice sample for more validation
#         if self.dense_sample:
#             print('=> Using dense sample for the dataset...')
#         if self.twice_sample:
#             print('=> Using twice sample for the dataset...')

#         if self.modality == 'RGBDiff':
#             self.data_length += 1  # Diff needs one more image to calculate diff
            
#         if dataset in ['kinetics', 'kineticsmini']:
#             self._parse_list_kinetics()
#         elif dataset in ['ucf101', 'hmdb51']:
#             self._parse_list_ucf101()
#         else:
#             self._parse_list()

#     def _load_image(self, directory, idx):
#         if self.modality == 'RGB' or self.modality == 'RGBDiff' or self.modality == 'HP':
#             return [Image.open(os.path.join(self.root_path, directory, self.image_tmpl.format(idx))).convert('RGB')]

#         elif self.modality == 'Flow':
#             x_img = Image.open(os.path.join(self.root_path, 'u', directory, self.image_tmpl.format(idx))).convert('L')
#             y_img = Image.open(os.path.join(self.root_path, 'v', directory, self.image_tmpl.format(idx))).convert('L')
#             return [x_img, y_img]

#     def _parse_list_ucf101(self):
#         # check the frame number is large >3:
#         with open(self.list_file, 'r') as fin:
#             reader = csv.reader(fin)
#             tmp = list(reader)
#         classes = [item[1] for item in tmp]
#         classes = list(set(classes))
#         classes.sort()
#         for item in tmp:
#             item[1] = classes.index(item[1])
#         if not self.test_mode or self.remove_missing:
#             tmp = [item for item in tmp if int(item[3]) >= self.data_length]
#         self.video_list = [UCF101VideoRecord(item, self.data_length) for item in tmp]

#         print('video number:%d' % (len(self.video_list)))
        
#     def _parse_list_kinetics(self):
#         # check the frame number is large >3:
#         with open(self.list_file, 'r') as fin:
#             reader = csv.reader(fin)
#             tmp = list(reader)
# #         tmp = [x.strip().split(' ') for x in open(self.list_file)]
#         if not self.test_mode or self.remove_missing:
#             tmp = [item for item in tmp if int(item[1]) >= self.data_length]
#         self.video_list = [VideoRecord(item, self.data_length) for item in tmp]

#         print('video number:%d' % (len(self.video_list)))
        
#     def _parse_list(self):
#         # check the frame number is large >3:
#         tmp = [x.strip().split(' ') for x in open(self.list_file)]
#         if not self.test_mode or self.remove_missing:
#             tmp = [item for item in tmp if int(item[1]) >= self.data_length]
#         self.video_list = [VideoRecord(item, self.data_length) for item in tmp]

#         if self.image_tmpl == '{:06d}-{}_{:05d}.jpg':
#             for v in self.video_list:
#                 v._data[1] = int(v._data[1]) / 2
#         print('video number:%d' % (len(self.video_list)))

#     def _sample_indices(self, record):
#         """

#         :param record: VideoRecord
#         :return: list
#         """
#         if self.dense_sample:  # i3d dense sample
#             sample_pos = max(1, 1 + record.num_frames - 64)
#             t_stride = 64 // self.num_segments
#             start_idx = 0 if sample_pos == 1 else np.random.randint(0, sample_pos - 1)
#             offsets = [(idx * t_stride + start_idx) % record.num_frames for idx in range(self.num_segments)]
#             return np.array(offsets) + 1
#         else:  # normal sample
#             average_duration = (record.num_frames - self.data_length + 1) // self.num_segments
#             if average_duration > 0:
#                 offsets = np.multiply(list(range(self.num_segments)), average_duration) + randint(average_duration,
#                                                                                                   size=self.num_segments)
#             elif record.num_frames > self.num_segments:
#                 offsets = np.sort(randint(record.num_frames - self.data_length + 1, size=self.num_segments))
#             else:
#                 offsets = np.zeros((self.num_segments,))
#             return offsets + 1

#     def _get_val_indices(self, record):
#         if self.dense_sample:  # i3d dense sample
#             sample_pos = max(1, 1 + record.num_frames - 64)
#             t_stride = 64 // self.num_segments
# #             start_idx = 0
#             start_idx = 0 if sample_pos == 1 else np.random.randint(0, sample_pos - 1)
#             offsets = [(idx * t_stride + start_idx) % record.num_frames for idx in range(self.num_segments)]
#             return np.array(offsets) + 1
#         else:
#             if record.num_frames > self.num_segments + self.data_length - 1:
#                 tick = (record.num_frames - self.data_length + 1) / float(self.num_segments)
#                 offsets = np.array([int(tick / 2.0 + tick * x) for x in range(self.num_segments)])
#             else:
#                 offsets = np.zeros((self.num_segments,))
#             return offsets + 1

#     def _get_test_indices(self, record):
#         if self.dense_sample:
#             sample_pos = max(1, 1 + record.num_frames - 64)
#             t_stride = 64 // self.num_segments
#             start_list = np.linspace(0, sample_pos - 1, num=10, dtype=int)
#             offsets = []
#             for start_idx in start_list.tolist():
#                 offsets += [(idx * t_stride + start_idx) % record.num_frames for idx in range(self.num_segments)]
#             return np.array(offsets) + 1
#         elif self.twice_sample:
#             tick = (record.num_frames - self.data_length + 1) / float(self.num_segments)

#             offsets = np.array([int(tick / 2.0 + tick * x) for x in range(self.num_segments)] +
#                                [int(tick * x) for x in range(self.num_segments)])

#             return offsets + 1
#         else:
#             tick = (record.num_frames - self.data_length + 1) / float(self.num_segments)
# #             rn = np.random.randint(0, tick+1)
# #             offsets = np.array([int(rn + tick * x) for x in range(self.num_segments)])
#             offsets = np.array([int(tick / 2.0 + tick * x) for x in range(self.num_segments)])
#             return offsets + 1


#     def get(self, record, indices):
#         images = list()
#         for seg_ind in indices:
#             p = int(seg_ind)
#             for i in range(self.data_length):
#                 seg_imgs = self._load_image(record.path, p)
#                 images.extend(seg_imgs)
#                 if p < record.num_frames:
#                     p += 1
#         # num_segments*data_length, num_channels, H, W
#         process_data = self.transform(images)
        
#         return process_data, record.label
    
    
#     def __getitem__(self, index):
#         record = self.video_list[index]

#         if not self.test_mode:
#             segment_indices = self._sample_indices(record) if self.random_shift else self._get_val_indices(record)
#         else:
#             segment_indices = self._get_test_indices(record)
            
#         return self.get(record, segment_indices)

#     def __len__(self):
#         return len(self.video_list)


import torch.utils.data as data

from PIL import Image
import os
import numpy as np
import csv
from numpy.random import randint


class VideoRecord(object):
    def __init__(self, row, data_length):
        self._data = row
        self._data_length = data_length

    @property
    def path(self):
        return self._data[0]

    @property
    def num_frames(self):
#         return int(self._data[1]) - self._data_length + 1
        return int(self._data[1])

    @property
    def label(self):
        return int(self._data[2])

class UCF101VideoRecord(object):
    def __init__(self, row, data_length):
        self._data = row
        self._data_length = data_length

    @property
    def path(self):
        return self._data[2]

    @property
    def num_frames(self):
        _len = int(self._data[3])
#         return _len - self._data_length + 1
        return _len
 
    @property
    def label(self):
        return int(self._data[1])
    
class TSNDataSet(data.Dataset):
    def __init__(self, dataset, root_path, list_file,
                 num_segments=3, data_length=1, modality='RGB',
                 image_tmpl='img_{:05d}.jpg', transform=None,
                 random_shift=True, test_mode=False,
                 remove_missing=False, dense_sample=False, twice_sample=False):
        self.root_path = root_path
        self.list_file = list_file
        self.num_segments = num_segments
        self.data_length = data_length
        self.modality = modality
        self.image_tmpl = image_tmpl
        self.transform = transform
        self.random_shift = random_shift
        self.test_mode = test_mode
        self.remove_missing = remove_missing
        self.dense_sample = dense_sample  # using dense sample as I3D
        self.twice_sample = twice_sample  # twice sample for more validation
        if self.dense_sample:
            print('=> Using dense sample for the dataset...')
        if self.twice_sample:
            print('=> Using twice sample for the dataset...')

        if self.modality == 'RGBDiff':
            self.data_length += 1  # Diff needs one more image to calculate diff
            
        if dataset in ['kinetics', 'kineticsmini']:
            self._parse_list_kinetics()
        elif dataset in ['ucf101', 'hmdb51']:
            self._parse_list_ucf101()
        else:
            self._parse_list()

    def _load_image(self, directory, idx):
        if self.modality in ['RGB', 'RGBDiff', 'HP', 'FlowNet', 'TVNet']:
            return [Image.open(os.path.join(self.root_path, directory, self.image_tmpl.format(idx))).convert('RGB')]
        elif self.modality == 'Flow':
            if self.image_tmpl == 'flow_{}_{:05d}.jpg':  # ucf
                x_img = Image.open(os.path.join(self.root_path, directory, self.image_tmpl.format('x', idx))).convert(
                    'L')
                y_img = Image.open(os.path.join(self.root_path, directory, self.image_tmpl.format('y', idx))).convert(
                    'L')
            elif self.image_tmpl == '{:06d}-{}_{:05d}.jpg':  # something v1 flow
                x_img = Image.open(os.path.join(self.root_path, '{:06d}'.format(int(directory)), self.image_tmpl.
                                                format(int(directory), 'x', idx))).convert('L')
                y_img = Image.open(os.path.join(self.root_path, '{:06d}'.format(int(directory)), self.image_tmpl.
                                                format(int(directory), 'y', idx))).convert('L')
            else:
                try:
                    # idx_skip = 1 + (idx-1)*5
                    flow = Image.open(os.path.join(self.root_path, directory, self.image_tmpl.format(idx))).convert('RGB')
                except Exception:
                    print('error loading flow file:',
                          os.path.join(self.root_path, directory, self.image_tmpl.format(idx)))
                    flow = Image.open(os.path.join(self.root_path, directory, self.image_tmpl.format(1))).convert('RGB')
                # the input flow file is RGB image with (flow_x, flow_y, blank) for each channel
                flow_x, flow_y, _ = flow.split()
                x_img = flow_x.convert('L')
                y_img = flow_y.convert('L')

            return [x_img, y_img]

    def _parse_list_ucf101(self):
        with open(self.list_file, 'r') as fin:
            reader = csv.reader(fin)
            tmp = list(reader)
        classes = [item[1] for item in tmp]
        classes = list(set(classes))
        classes.sort()
        for item in tmp:
            item[1] = classes.index(item[1])
        if self.modality == 'Flow':
            for item in tmp:
                item[3] = int(item[3]) - 1
        if not self.test_mode or self.remove_missing:
            tmp = [item for item in tmp if int(item[3]) >= self.data_length]
        self.video_list = [UCF101VideoRecord(item, self.data_length) for item in tmp]

        print('video number:%d' % (len(self.video_list)))
        
    def _parse_list_kinetics(self):
        with open(self.list_file, 'r') as fin:
            reader = csv.reader(fin)
            tmp = list(reader)
        if self.modality == 'Flow':
            for item in tmp:
                item[1] = int(item[1]) - 1
        if not self.test_mode or self.remove_missing:
            tmp = [item for item in tmp if int(item[1]) >= self.data_length]
        self.video_list = [VideoRecord(item, self.data_length) for item in tmp]

        print('video number:%d' % (len(self.video_list)))
        
    def _parse_list(self):
        tmp = [x.strip().split(' ') for x in open(self.list_file)]
        if self.modality == 'Flow':
            for item in tmp:
                item[1] = int(item[1]) - 1
        if not self.test_mode or self.remove_missing:
            tmp = [item for item in tmp if int(item[1]) >= self.data_length]
        self.video_list = [VideoRecord(item, self.data_length) for item in tmp]
        
#         if self.image_tmpl == '{:06d}-{}_{:05d}.jpg':
#             for v in self.video_list:
#                 v._data[1] = int(v._data[1]) / 2
        print('video number:%d' % (len(self.video_list)))

    def _sample_indices(self, record):
        """

        :param record: VideoRecord
        :return: list
        """
        if self.dense_sample:  # i3d dense sample
            if self.data_length == 1:
                sample_pos = max(1, 1 + record.num_frames - 64)
                t_stride = 64 // self.num_segments
                start_idx = 0 if sample_pos == 1 else np.random.randint(0, sample_pos - 1)
                offsets = [(idx * t_stride + start_idx) % record.num_frames for idx in range(self.num_segments)]
            else:
                sample_pos = max(1, 1 + record.num_frames - self.data_length*self.num_segments)
                start_idx = 0 if sample_pos == 1 else np.random.randint(0, sample_pos - 1)
                offsets = [(idx * self.data_length + start_idx) % record.num_frames for idx in range(self.num_segments)]
            return np.array(offsets) + 1
        else:  # normal sample
            average_duration = (record.num_frames - self.data_length + 1) // self.num_segments
            if average_duration > 0:
                offsets = np.multiply(list(range(self.num_segments)), average_duration) + randint(average_duration, size=self.num_segments)
            elif record.num_frames > self.num_segments:
                offsets = np.sort(randint(record.num_frames - self.data_length + 1, size=self.num_segments))
            else:
                offsets = np.zeros((self.num_segments,))
            return offsets + 1

    def _get_val_indices(self, record):
        if self.dense_sample:  # i3d dense sample
            if self.data_length == 1:
                sample_pos = max(1, 1 + record.num_frames - 64)
                t_stride = 64 // self.num_segments
    #             start_idx = 0
                start_idx = 0 if sample_pos == 1 else np.random.randint(0, sample_pos - 1)
                offsets = [(idx * t_stride + start_idx) % record.num_frames for idx in range(self.num_segments)]
            else:
                sample_pos = max(1, 1 + record.num_frames - self.data_length*self.num_segments)
                start_idx = 0 if sample_pos == 1 else np.random.randint(0, sample_pos - 1)
                offsets = [(idx * self.data_length + start_idx) % record.num_frames for idx in range(self.num_segments)]
            return np.array(offsets) + 1    
        else:
            if record.num_frames > self.num_segments + self.data_length - 1:
                tick = (record.num_frames - self.data_length + 1) / float(self.num_segments)
                offsets = np.array([int(tick / 2.0 + tick * x) for x in range(self.num_segments)])
            else:
                offsets = np.zeros((self.num_segments,))
            return offsets + 1

    def _get_test_indices(self, record):
        if self.dense_sample:
            if self.data_length == 1:
                sample_pos = max(1, 1 + record.num_frames - 64)
                t_stride = 64 // self.num_segments
                start_list = np.linspace(0, sample_pos - 1, num=10, dtype=int)
                offsets = []
                for start_idx in start_list.tolist():
                    offsets += [(idx * t_stride + start_idx) % record.num_frames for idx in range(self.num_segments)]
            else:
                sample_pos = max(1, 1 + record.num_frames - self.data_length*self.num_segments)
                start_list = np.linspace(0, sample_pos - 1, num=10, dtype=int)
                offsets = []
                for start_idx in start_list.tolist():
                    offsets += [(idx * self.data_length + start_idx) % record.num_frames for idx in range(self.num_segments)]
            return np.array(offsets) + 1
        elif self.twice_sample:
            tick = (record.num_frames - self.data_length + 1) / float(self.num_segments)

            offsets = np.array([int(tick / 2.0 + tick * x) for x in range(self.num_segments)] +
                               [int(tick * x) for x in range(self.num_segments)])

            return offsets + 1
        else:
            tick = (record.num_frames - self.data_length + 1) / float(self.num_segments)
#             rn = np.random.randint(0, tick+1)
#             offsets = np.array([int(rn + tick * x) for x in range(self.num_segments)])
            offsets = np.array([int(tick / 2.0 + tick * x) for x in range(self.num_segments)])
            return offsets + 1


    def get(self, record, indices):
        images = list()
        for seg_ind in indices:
            p = int(seg_ind)
            for i in range(self.data_length):
                seg_imgs = self._load_image(record.path, p)
                images.extend(seg_imgs)
                if p < record.num_frames:
                    p += 1
        # num_segments*data_length, num_channels, H, W
        process_data = self.transform(images)
        
        return process_data, record.label
    
    
    def __getitem__(self, index):
        record = self.video_list[index]

        if not self.test_mode:
            segment_indices = self._sample_indices(record) if self.random_shift else self._get_val_indices(record)
        else:
            segment_indices = self._get_test_indices(record)
            
        return self.get(record, segment_indices)

    def __len__(self):
        return len(self.video_list)
