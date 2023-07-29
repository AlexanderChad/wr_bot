import os
import subprocess
import sys
import time
import cv2
import numpy as np

work_dir:str #рабочая директория
screenshot_path:str #пусть к скриншоту
img_rgb:np.ndarray # скриншот
target_images:np.ndarray=['ad_disable', 'ad_enable', 'ad_exit_next0', 'ad_exit_next1', 'ad_exit0', 'ad_exit1', 'box_open', 'main_menu', 'main_menu_exit', 'discount_banner0', 'discount_banner1', 'discount_banner2', 'back', 'bronze_box']
target_images_rgb={} #загруженные целевые изображения
target_recognized={} #распознанные целевые изображения на скриншоте
threshold = 0.7 #порог распознавания
wm_size=[] #размер экрана в пикселях

def printLog(str_log):
    print(time.strftime("%X\t", time.localtime()) + str_log)

def load_target_images():
    global target_images_rgb
    for img_t in target_images:
        target_images_rgb[img_t]=cv2.imread(f"{work_dir}\\images\\{img_t}.png")
    #target_images = next(os.walk(f"{work_dir}\\images"), (None, None, []))[2]


def get_screenshot():
    global img_rgb
    printLog("get_screenshot started")
    if (os.path.exists(screenshot_path)):
        if (os.path.getsize(screenshot_path))>0:
            os.remove(screenshot_path)
    os.system(f"C:\\ADB\\adb.exe exec-out screencap -p > {screenshot_path}")
    if (os.path.exists(screenshot_path)):
        if (os.path.getsize(screenshot_path))>0:
            img_rgb = cv2.imread(f'{work_dir}\\temp\\screenshot.png')
            return True
        else:
            return False
        
def recognize_screenshot():
    global target_recognized, img_rgb
    printLog("recognize_screenshot started")
    for img_t in target_images:
        res = cv2.matchTemplate(img_rgb,target_images_rgb[img_t],cv2.TM_CCOEFF_NORMED)
        loc = np.where(res >= threshold)
        target_recognized[img_t]=True if (len(loc[0])>0) else False
        printLog(f"Img: {img_t} - {target_recognized[img_t]}")
    printLog("recognize_screenshot is complete.")

def convert_xy_position(x,y):
    SurfaceOrientation=int(subprocess.run(['C:\\ADB\\adb.exe', 'shell', 'dumpsys input | grep SurfaceOrientation | awk "{print $2}" | head -n 1'], capture_output=True, text=True).stdout[26:-1])
    printLog(f'SurfaceOrientation: {SurfaceOrientation}')
    if SurfaceOrientation==0:
        new_x=x
        new_y=y
    elif SurfaceOrientation==1:
        new_x=wm_size[0]-y
        new_y=x
    elif SurfaceOrientation==2:
        new_x=wm_size[0]-x
        new_y=wm_size[1]-y 
    elif SurfaceOrientation==3:
        new_x=y
        new_y=wm_size[1]-x
    return new_x, new_y

def tap_screen(x, y):
    #cx,cy=convert_xy_position(x,y)
    ret=subprocess.run(['C:\\ADB\\adb.exe', 'shell', f'input tap {x} {y}'], capture_output=True, text=True).stdout
    #printLog(f"tap x:{x}, y:{y}, cmd: x:{cx}, y:{cy}")
    printLog(f"tap x:{x}, y:{y}")

def au_worker():
    if (target_recognized['discount_banner0'] or target_recognized['discount_banner1']) and target_recognized['main_menu_exit']:
        tap_screen(2208, 56)
    elif target_recognized['discount_banner2']:
        tap_screen(1764, 267)
    elif target_recognized['main_menu']:
        tap_screen(62, 720)
    elif target_recognized['box_open']:
        tap_screen(652, 744)
    elif target_recognized['ad_exit_next0'] or target_recognized['ad_exit_next1'] or target_recognized['ad_exit0'] or target_recognized['ad_exit1']:
        tap_screen(2195, 66)
    elif target_recognized['back'] and target_recognized['bronze_box']:
        tap_screen(100, 1024)


if __name__ == "__main__":
    printLog("Starting wr_bot")

    work_dir=os.path.abspath(os.path.dirname(sys.argv[0]))
    screenshot_path=f'{work_dir}\\temp\\screenshot.png'
    printLog(f'Running from: {work_dir}')

    printLog("Loading target images...")
    load_target_images()
    printLog("Loading is complete.")

    ret=subprocess.run(['C:\\ADB\\adb.exe', 'devices'], capture_output=True, text=True).stdout
    printLog(f'Devices: {ret}')
    '''
    #получаем разрешение экрана
    ret=subprocess.run(['C:\\ADB\\adb.exe', 'shell', 'wm size'], capture_output=True, text=True).stdout
    wm_size_text=ret[15:-1].split('x') #получаем из ответа ху в строковом виде
    wm_size=[int(wm_size_text[0]), int(wm_size_text[1])] #сохраняем как числовые для вычислений
    printLog(f'Device display size: x={wm_size[0]}, y={wm_size[1]}')
    '''

    while(1):
        printLog("Loop")
        if get_screenshot():
            recognize_screenshot()
            au_worker()
        time.sleep(1)
        printLog("End")

    
    printLog("Exit")
