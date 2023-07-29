import os
import subprocess
import sys
import time
import cv2
import numpy as np

work_dir:str #рабочая директория
screenshot_path:str #пусть к скриншоту
img_rgb:np.ndarray # скриншот
target_images:np.ndarray=['ad_disable', 'ad_enable', 'black_market', 'ad_exit_next0', 'ad_exit_next1', 'ad_exit_next2', 'ad_exit0', 'ad_exit1', 'ad_exit2', 'box_open', 'main_menu', 'main_menu_exit', 'discount_banner0', 'discount_banner1', 'discount_banner2', 'back', 'bronze_box']
target_images_rgb={} #загруженные целевые изображения
target_images_psize={} #половинный размеры загруженных целевых изображений
target_recognized={} #распознанные целевые изображения на скриншоте
threshold = 0.7 #порог распознавания

def printLog(str_log):
    print(time.strftime("%X\t", time.localtime()) + str_log)

def load_target_images():
    global target_images_rgb
    for img_t in target_images:
        target_images_rgb[img_t]=cv2.imread(f"{work_dir}\\images\\{img_t}.png") #загружаем в память
        _, w, h = target_images_rgb[img_t].shape[::-1] #получаем размеры
        target_images_psize[img_t]=[w//2,h//2]

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
        #получаем координаты и вероятности
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        #получаем координаты центра
        cx=max_loc[0]+target_images_psize[img_t][0]
        cy=max_loc[1]+target_images_psize[img_t][1]
        #записываем результаты
        target_recognized[img_t]=[True if (max_val>threshold) else False, cx, cy]
        printLog(f"Img: {img_t} - {target_recognized[img_t][0]}, location: x:{cx}, y:{cy}")
    printLog("recognize_screenshot is complete.")

def tap_screen(x, y):
    subprocess.run(['C:\\ADB\\adb.exe', 'shell', f'input tap {x} {y}'])
    printLog(f"tap x:{x}, y:{y}")

def au_worker():
    if (target_recognized['discount_banner0'][0] or target_recognized['discount_banner1'][0]) and target_recognized['main_menu_exit'][0]: #первый тип акционного банера, закрываем
        tap_screen(target_recognized['main_menu_exit'][1], target_recognized['main_menu_exit'][2])
    elif target_recognized['discount_banner2'][0]: #второй тип акционного банера, закрываем
        tap_screen(1764, 267)
    elif target_recognized['main_menu'][0]: #если в начальном меню, то идем в коробки
        tap_screen(62, 720)
    elif target_recognized['box_open'][0]: #если можем открыть коробку
        tap_screen(652, 744)
    elif target_recognized['black_market'][0]: #если нельзя открыть бесплатно коробку (мы в меню коробок), то завершаем скрипт
        printLog("black_market closed. Exit.")
        sys.exit()  # завершаем программу
    elif target_recognized['back'][0] and target_recognized['bronze_box'][0]: #если покрутили рулетку, то выходим из коробки
        tap_screen(100, 1024)
    else:
        for ad_e in {'ad_exit_next0', 'ad_exit_next1', 'ad_exit_next2', 'ad_exit0', 'ad_exit1', 'ad_exit2'}: #ищем кнопки для выхода из рекламы
            if target_recognized[ad_e][0]:
                tap_screen(target_recognized[ad_e][1], target_recognized[ad_e][2])

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

    while(1):
        printLog("Loop")
        if get_screenshot(): #пытаемся получить скриншот, если получили
            recognize_screenshot() #распознаем все что знаем
            au_worker() #принимаем действия
            time.sleep(1) #после выполнения действий даем время на анимацию (загрузку активити)
        printLog("Loop end")
    printLog("Exit.")
