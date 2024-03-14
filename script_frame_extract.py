import os
current_path = os.path.dirname(os.path.abspath(__file__))
"""
The script facilitates a clearer and faster execution of the project.
This is the FIRST script.
You may need to edit: parent_dir, proj_dir, start_frame_idx, extract_cams
1. When new data is recorded, the audio and video first need to be aligned. (MANUALLY)
2. FRAME EXTRACT (Run this script)
3.1. Label the cello/violin key points. (MANUALLY)
3.2. Camera Calibration (MANUALLY)
"""

parent_dir = 'cello_1113'
proj_dir = 'cello_1113_pgy'
start_frame_idx = 133  # obtained by audio and video alignment
end_frame_idx = 647
# extract_cams = ['21334181', '21334190', '21334237']  # cello
extract_cams = ['21334181']  # cello overlay
# extract_cams = ['21334220', '21334207']  # violin
# extract_cams = ['21334220']  # violin overlay
extract_frames = [start_frame_idx]
# extract_frames = [start_frame_idx, 300]  # extract more frames for TRACKKEYPOINTS (more labels)

extract_frames = [i for i in range(start_frame_idx, end_frame_idx+1)]  # for overlay

"""
FRAME EXTRACT
cello cameras: 21334181, 21334190, 21334237(optional, could be out of focus)
violin cameras: 21334220, 21334207
Extracted frames are used to track key points on the instrument.
"""

for extract_cam in extract_cams:
    for extract_frame in extract_frames:
        files_path = f'{current_path}/data/{parent_dir}/{proj_dir}/videos/{proj_dir}_{extract_cam}.avi'
        output_path = f'{current_path}/data/{parent_dir}/{proj_dir}/frames'
        # output_path = f'{current_path}/cello_kp_2d/labeled_jsons/{proj_dir}'

        frame_extract_command = f'python ./tools/frame_extract_pipeline.py ' \
                                f'--files_path {files_path} ' \
                                f'--output_path {output_path} ' \
                                f'--start_frame_idx {extract_frame} ' \
                                f'--end_frame_idx {extract_frame+1}'
        os.system(frame_extract_command)
