import argparse
import numpy as np
import cv2
import tensorflow as tf
from utils.utils import get_face_points, normalize_wrt_maximum_distance_point
from utils.img_utils import draw_key_points_pose, draw_axis
from utils.utils_tflite import initialize_interpreter, resize_preserving_ar, inference_interpreter, pose_from_det


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("-dm", "--detection-model", type=str, default=None, help="PATH_DETECTION_MODEL", required=True)
    ap.add_argument("-pm", "--pose-model", type=str, default=None, help="PATH_POSE_MODEL", required=True)
    ap.add_argument("-hm", "--hhp-model", type=str, default=None, help="PATH_HPPNET", required=True)
    ap.add_argument("-i", "--image", type=str, default=None, help="PATH_IMAGE", required=True)

    config = ap.parse_args()
    tf.keras.backend.clear_session()

    hhp_model = tf.keras.models.load_model(config.hhp_model, custom_objects={"tf": tf})
    length_axis = 50

    img = cv2.imread(config.image)
    # print("1", aux_img.shape)

    interpreter_od, input_shape_model_od, input_details_od = initialize_interpreter(config.detection_model)
    interpreter_pose, input_shape_interpreter_pose, input_details_pose = initialize_interpreter(config.pose_model)

    resized_img, new_old_shape = resize_preserving_ar(img, input_shape_model_od)
    # print("2", img.shape, new_old_shape)
    # cv2.imshow("", img)
    # cv2.waitKey(0)

    boxes, classes, scores, num_det = inference_interpreter(interpreter_od, resized_img, input_details_od)
    # print(boxes, classes, scores, num_det)
    # draw_aux(img, boxes)
    # exit()

    kpt = pose_from_det(resized_img, boxes, classes, scores, interpreter_pose, input_shape_interpreter_pose, input_details_pose, img, new_old_shape, False, 0.3)

    # print("XX", kpt)
    img_res = img.copy()

    # print("BBB", aux_img.shape)

    for kpt_person in kpt:
        for elem in kpt_person:
            elem[0] = elem[0] * img.shape[0]
            elem[1] = elem[1] * img.shape[1]

        # img_res = draw_key_points_pose(img_res, kpt_person)

        face_kpt = get_face_points(kpt_person, 'centernet')

        mean_x = np.mean([face_kpt[i] for i in range(0, 15, 3) if face_kpt[i] != 0.0])
        mean_y = np.mean([face_kpt[i + 1] for i in range(0, 15, 3) if face_kpt[i + 1] != 0.0])

        face_kpt_normalized = np.array(normalize_wrt_maximum_distance_point(face_kpt, mean_x, mean_y))

        input_kpts = tf.cast(np.expand_dims(face_kpt_normalized, 0), tf.float32)

        y, p, r = hhp_model(input_kpts, training=False)

        yaw, yaw_unc = y[:, 0].numpy()[0], y[:, 1].numpy()[0]
        pitch, pitch_unc = p[:, 0].numpy()[0], p[:, 1].numpy()[0]
        roll, roll_unc = r[:, 0].numpy()[0], r[:, 1].numpy()[0]

        img_res = draw_axis(yaw, pitch, roll, img_res, mean_x, mean_y, length_axis, yaw_unc, pitch_unc, roll_unc)

    cv2.imwrite('/home/imavis/Desktop/ttttemp/fast_1_pose.png', cv2.resize(img_res, (720, 440)))

    # cv2.imshow("", img_res)
    # cv2.waitKey(0)


