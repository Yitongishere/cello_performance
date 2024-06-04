import sys
sys.path.append('..')
import argparse
import glob
import re
import cv2
import numpy as np
import json
import os
import matplotlib.pyplot as plt
import torch
import traceback
from icecream import ic
import mmcv
from mmcv import imread
import mmengine
from mmengine.registry import init_default_scope
from mmpose.apis import inference_topdown
from mmpose.apis import init_model as init_pose_estimator
from mmpose.evaluation.functional import nms
from mmpose.registry import VISUALIZERS
from mmpose.structures import merge_data_samples
from mmdet.apis import inference_detector, init_detector
from tools.rotate import frame_rotate
import requests
import gdown

'''
configs and models for pose estimator (2d kept detection) and detector (bbox detection) should be prepared ahead
preferred pose estimator model link: https://drive.google.com/file/d/1Oy9O18cYk8Dk776DbxpCPWmJtJCl-OCm/

We give a method in the script using gdown to download the model from googledrive.
'''


def visualize(pose_estimator, img, data_samples):
    # 半径
    pose_estimator.cfg.visualizer.radius = 2
    # 线宽
    pose_estimator.cfg.visualizer.line_width = 1
    # pose_estimator.cfg.visualizer.setdefault('save_dir', 'outputs')
    pose_estimator.cfg.visualizer.setdefault('save_dir', None)
    visualizer = VISUALIZERS.build(pose_estimator.cfg.visualizer)
    # 元数据
    visualizer.set_dataset_meta(pose_estimator.dataset_meta)
    img = mmcv.imread(img, channel_order='bgr')  # when cv2.imshow is used
    # img = mmcv.imread(img, channel_order='rgb') # when plt is used
    img_output = visualizer.add_datasample(
        'result',
        img,
        data_sample=data_samples,
        draw_gt=False,
        # draw_heatmap=True, # comment this if you want to output videos
        draw_bbox=True,
        show_kpt_idx=False,
        # show=True,
        show=False,
        wait_time=0
    )
    # plt.figure(figsize=(10, 10))
    # plt.imshow(img_output)
    # plt.show()
    return img_output


def posinfo2json(pose, path='json/pos.json', save=True, kp_type='unit8'):
    file_name_split = path.split('.')[:-1]
    if len(file_name_split) == 1:
        jsonfile = ''.join(file_name_split)
    else:
        jsonfile = '.'.join(file_name_split)
    kp_info = pose[0].to_dict()['pred_instances']

    output = np.concatenate(
        (np.array(kp_info['keypoints'][0]), kp_info['keypoint_scores'].reshape(-1, 1)), axis=1)

    try:
        print(jsonfile)
        with open(os.path.abspath(jsonfile + '.json'), 'w') as f:
            f.write(json.dumps(output.tolist()))
        f.close()
    except IOError:
        traceback.print_exc()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='infer_pipeline')
    parser.add_argument('--dirs_path', default='../data/cello_1113/cello_1113_scale/video/cello_1113_21334190.avi',
                        type=str, required=True)
    parser.add_argument('--proj_dir', default='cello_1113_scale', type=str, required=True)
    parser.add_argument('--end_frame_idx', default='2', type=int, required=True)
    parser.add_argument('--start_frame_idx', default='1', type=int, required=False)
    args = parser.parse_args()
    dirs_path = args.dirs_path
    proj_dir = args.proj_dir
    end_frame_idx = args.end_frame_idx
    start_frame_idx = args.start_frame_idx
    
    device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
    DET_CONF_THRES = 0.5
    detector = init_detector(
        'configs/rtmdet_m_640-8xb32_coco-person.py',
        'https://download.openmmlab.com/mmpose/v1/projects/rtmpose/rtmdet_m_8xb32-100e_coco-obj365-person-235e8209.pth',
        device=device
    )
    
    if not os.path.exists('./dw-ll_ucoco_384.pth'):
        dwpose_model_url = 'https://drive.google.com/uc?id=1Oy9O18cYk8Dk776DbxpCPWmJtJCl-OCm'
        try:
            gdown.download(dwpose_model_url, './dw-ll_ucoco_384.pth', quiet = False)
        except:
            raise requests.exceptions.ConnectTimeout(
              'Please download the checkpoint file at "{}" and'
              'put it into the folder "./" manually!\n'.format('https://drive.google.com/file/d/1Oy9O18cYk8Dk776DbxpCPWmJtJCl-OCm/'))
        
    pose_estimator = init_pose_estimator(
        'configs/rtmpose-l_8xb32-270e_coco-ubody-wholebody-384x288.py',
        './dw-ll_ucoco_384.pth',  # your pose estimator model.pth path
        device=device,
        # if you want to see heatmaps, please uncomment the following line (but it'll be much slower)
        # cfg_options={'model': {'test_cfg': {'output_heatmaps': True}}}
    )

    # dirs_path = r'../data/cello/cello_01'  # Your directory path
    #dirs_list = os.listdir(dirs_path)
    #full_path = [dirs_path + os.sep + i for i in dirs_list]  # multiple proj
    full_path = [dirs_path]  # single proj
    for idx, dir_path in enumerate(full_path):
        print(dir_path)
        videos_path = glob.glob(dir_path + os.sep + '*.avi')
        print(videos_path)
        base_name = [os.path.basename(i) for i in videos_path]
        file_name = [os.path.splitext(i)[0] for i in base_name]
        cam_num = [i.split('_')[-1] for i in file_name]
        # sub_dir_name = dirs_list[idx]  # multiple proj
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        for i, video_path in enumerate(videos_path):
            cap = cv2.VideoCapture(video_path)
            frame_num = 1
            if not os.path.exists('./kp_result'):
                os.makedirs('./kp_result', exist_ok=True)
            # store_path = r'./kp_result/{sub_dir_name}/{cam_num}'.format(sub_dir_name=sub_dir_name,
            #                                                             cam_num=cam_num[i])
            store_path = r'./kp_result/{dir_name}/{cam_num}'.format(dir_name=proj_dir,
                                                                    cam_num=cam_num[i])
            if not os.path.exists(store_path):
                os.makedirs(store_path, exist_ok=True)
            out = cv2.VideoWriter(f'{store_path}/output.avi', fourcc, fps=30, frameSize=(2300, 2656))
            while True:
                # TODO edit end_frame num
                if frame_num == end_frame_idx:
                    break
                if frame_num >= start_frame_idx:
                    ret, frame = cap.read()
                    if not ret:
                        break
                    frame_rot = frame_rotate(cam_num[i], frame)
                    init_default_scope(detector.cfg.get('default_scope', 'mmdet'))
                    detect_result = inference_detector(detector, frame_rot)
                    pred_instance = detect_result.pred_instances.cpu().numpy()
                    bboxes = np.concatenate((pred_instance.bboxes, pred_instance.scores[:, None]), axis=1)
                    bboxes = bboxes[np.logical_and(pred_instance.labels == 0, pred_instance.scores > DET_CONF_THRES)]
                    bboxes = bboxes[nms(bboxes, 0.3)][:, :4]
                    init_default_scope(pose_estimator.cfg.get('default_scope', 'mmpose'))
                    # bboxes=None indicates that the entire image will be regarded as a single bbox area (one person)
                    pose_results = inference_topdown(pose_estimator, frame_rot, bboxes=bboxes)
                    data_samples = merge_data_samples(pose_results)
                    result_img = visualize(pose_estimator, frame_rot, data_samples)
                    # store 2d key points result to json file
                    posinfo2json(pose_results, f'{store_path}/{frame_num}.json')
                    out.write(result_img)
                    # cv2.imshow('result', result_img)
                    # cv2.waitKey(1)
                frame_num += 1
                
            cap.release()
            out.release()
        cv2.destroyAllWindows()
