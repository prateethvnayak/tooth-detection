# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import hashlib
import tensorflow as tf
import os
import logging
import io
from lxml import etree
import PIL.Image

from object_detection.utils import label_map_util
from object_detection.utils import dataset_util

r"""Convert raw PASCAL dataset type to TFRecord for object_detection.

Example usage:
    python object_detection/dataset_tools/create_pascal_tf_record.py \
        --data_dir=/home/user/VOCdevkit \
        --output_path=/home/user/pascal.record
"""


flags = tf.app.flags
flags.DEFINE_string('data_dir', '', 'Root directory to raw PASCAL VOC dataset.')
flags.DEFINE_string('category', '6mand', 'Root directory to raw PASCAL VOC dataset.')
flags.DEFINE_string('set', 'train', 'Convert training set, validation set or '
                    'merged set.')
flags.DEFINE_string('annotations_dir', 'Annotations',
                    '(Relative) path to annotations directory.')
flags.DEFINE_string('output_path', 'noor.record', 'Path to output TFRecord')
flags.DEFINE_string('label_map_path', 'noor_dataset/Annoted/' + flags.FLAGS.category + '/pascal_label_map.pbtxt',
                    'Path to label map proto')
SETS = ['train', 'val', 'trainval', 'test']
FLAGS = flags.FLAGS


def create_directory_if_not_exists(directory):
  if not os.path.exists(directory):
    os.makedirs(directory)

def save_cropped_images(data,
                        dataset_directory,
                        label_map_dict,
                        image_subdirectory = 'JPEGImages',
                        output_directory = FLAGS.set,
                        category = FLAGS.category,
                        dataset_name = 'custom'):

  output_dir_dict = {16: '6max', 26: '6max', 36: '6mand', 46: '6mand'}
  create_directory_if_not_exists(output_directory)
  create_directory_if_not_exists(os.path.join(output_directory, output_dir_dict[category]))
  full_path = os.path.join(dataset_directory, image_subdirectory, data['filename'] + '.png')
  with tf.gfile.GFile(full_path, 'rb') as fid:
    encoded_jpg = fid.read()
  encoded_jpg_io = io.BytesIO(encoded_jpg)
  image = PIL.Image.open(encoded_jpg_io)

  for i, obj in enumerate(data['object']):
    if int(obj['name']) != category:
        continue
    xmin = float(obj['bndbox']['xmin'])
    ymin = float(obj['bndbox']['ymin'])
    xmax = float(obj['bndbox']['xmax'])
    ymax = float(obj['bndbox']['ymax'])
    path = os.path.join(output_directory, output_dir_dict[category], dataset_name + str(data['filename']) + '-' + str(i) + '.png')
    print(path)
    image.crop((xmin, ymin, xmax, ymax)).resize((50, 100)).convert('LA').save(path)

def dict_to_tf_example(data,
                       dataset_directory,
                       label_map_dict,
                       image_subdirectory='JPEGImages'):
  """Convert XML derived dict to tf.Example proto.

  Notice that this function normalizes the bounding box coordinates provided
  by the raw data.

  Args:
    data: dict holding PASCAL XML fields for a single image (obtained by
      running dataset_util.recursive_parse_xml_to_dict)
    dataset_directory: Path to root directory holding PASCAL dataset
    label_map_dict: A map from string label names to integers ids.
    ignore_difficult_instances: Whether to skip difficult instances in the
      dataset  (default: False).
    image_subdirectory: String specifying subdirectory within the
      PASCAL dataset directory holding the actual image data.

  Returns:
    example: The converted tf.Example.

  Raises:
    ValueError: if the image pointed to by data['filename'] is not a valid JPEG
  """
  data_dir = os.path.join('noor_dataset', 'Annoted', '6mand')
  img_path = os.path.join(data_dir, image_subdirectory, data['filename'])
  full_path = os.path.join(dataset_directory, img_path + '.png')
  print('full_path', full_path)
  with tf.gfile.GFile(full_path, 'rb') as fid:
    encoded_jpg = fid.read()
  encoded_jpg_io = io.BytesIO(encoded_jpg)
  image = PIL.Image.open(encoded_jpg_io)
  if image.format != 'JPEG': #TODO be sure that all PNG work with this
    raise ValueError('Image format not JPEG')
  key = hashlib.sha256(encoded_jpg).hexdigest()

  width = int(data['size']['width'])
  height = int(data['size']['height'])

  xmin = []
  ymin = []
  xmax = []
  ymax = []
  classes = []
  classes_text = []
  if 'object' not in data.keys():
      print('No label detected in the xml format')
      return
  for obj in data['object']:
    xmin.append(float(obj['bndbox']['xmin']) / width)
    ymin.append(float(obj['bndbox']['ymin']) / height)
    xmax.append(float(obj['bndbox']['xmax']) / width)
    ymax.append(float(obj['bndbox']['ymax']) / height)
    classes_text.append(obj['name'].encode('utf8'))
    classes.append(label_map_dict[obj['name']])

  example = tf.train.Example(features=tf.train.Features(feature={
      'image/height': dataset_util.int64_feature(height),
      'image/width': dataset_util.int64_feature(width),
      'image/filename': dataset_util.bytes_feature(
          data['filename'].encode('utf8')),
      'image/source_id': dataset_util.bytes_feature(
          data['filename'].encode('utf8')),
      'image/key/sha256': dataset_util.bytes_feature(key.encode('utf8')),
      'image/encoded': dataset_util.bytes_feature(encoded_jpg),
      'image/format': dataset_util.bytes_feature('jpeg'.encode('utf8')),
      'image/object/bbox/xmin': dataset_util.float_list_feature(xmin),
      'image/object/bbox/xmax': dataset_util.float_list_feature(xmax),
      'image/object/bbox/ymin': dataset_util.float_list_feature(ymin),
      'image/object/bbox/ymax': dataset_util.float_list_feature(ymax),
      'image/object/class/text': dataset_util.bytes_list_feature(classes_text),
      'image/object/class/label': dataset_util.int64_list_feature(classes),
  }))
  return example

def main(_):
  writer = tf.python_io.TFRecordWriter(FLAGS.output_path)
  datasets = ['custom', 'google-image', 'noor']
  categories = [16, 26, 36, 46]
  output_dir_dict = {16: '6max', 26: '6max', 36: '6mand', 46: '6mand'}
  for dataset in datasets:
      data_dir = os.path.join('data', dataset)
      for category in categories:
          examples_path = os.path.join(data_dir, 'ImageSets', 'Main', str(category) + '_' + FLAGS.set + '.txt')
          label_map_dict = label_map_util.get_label_map_dict(os.path.join(data_dir, 'pascal_label_map.pbtxt'))
          print('label_map_dict', label_map_dict)
          annotations_dir = os.path.join(data_dir, FLAGS.annotations_dir)
          examples_list = dataset_util.read_examples_list(examples_path)
          examples_list = [x for x in examples_list if x]
          print(examples_list)

          for idx, example in enumerate(examples_list):
            if idx % 100 == 0:
              logging.info('On image %d of %d', idx, len(examples_list))
            path = os.path.join(annotations_dir, example + '.xml')
            with tf.gfile.GFile(path, 'r') as fid:
              xml_str = fid.read()
            xml = etree.fromstring(xml_str)
            data = dataset_util.recursive_parse_xml_to_dict(xml)['annotation']
            if 'object' not in data.keys():
                print('No label, ignoring ', path)
                continue
            save_cropped_images(data, data_dir, label_map_dict, category=category, dataset_name = dataset)



      #   tf_example = dict_to_tf_example(data, FLAGS.data_dir, label_map_dict)
      #   writer.write(tf_example.SerializeToString())
      # writer.close()


if __name__ == '__main__':
  tf.app.run()