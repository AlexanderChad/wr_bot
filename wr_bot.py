import os
import subprocess
import sys
import time
import cv2
import numpy as np

work_dir:str #рабочая директория
screenshot_path:str #пусть к скриншоту
img_rgb:np.ndarray # скриншот
target_images:np.ndarray=['ad_enable', 'ruletka', 'ruletka_attemp', 'ruletka_end', 'get', 'ok', 'black_market', 'discount_special', 'ad_exit_next0', 'ad_exit_next1', 'ad_exit_next2', 'ad_exit0', 'ad_exit1', 'ad_exit2', 'box_open', 'main_menu', 'main_menu_exit', 'discount_banner0', 'discount_banner1', 'discount_banner2', 'back', 'bronze_box']
target_images_rgb={} #загруженные целевые изображения
target_images_psize={} #половинный размеры загруженных целевых изображений
target_recognized={} #распознанные целевые изображения на скриншоте
threshold=0.85 #порог распознавания
discount_special_cn=0 #пункт меню специальных предложений
start_time_ad:time #время начала видео
timeout_ad=90 #время, отведенное на рекламу
ad_mode=False #режим просмотра рекламы
ruletka_mode=True #режим рулетки, False - когда уже потратили все попытки

def printLog(str_log): #лог в формате: время и информация
    print(time.strftime("%X\t", time.localtime()) + str_log)

def load_target_images(): #загружаем целевые картинки
    global target_images_rgb
    for img_t in target_images: #перебираем
        target_images_rgb[img_t]=cv2.imread(f"{work_dir}\\images\\{img_t}.png") #загружаем в память
        _, w, h = target_images_rgb[img_t].shape[::-1] #получаем размеры
        target_images_psize[img_t]=[w//2,h//2] #записываем половинные

def get_screenshot(): #получаем с устройства скриншот, возвращаем результат получения
    global img_rgb
    printLog("get_screenshot started")
    if (os.path.exists(screenshot_path)):
        os.remove(screenshot_path) #удаляем файл если он существует
    os.system(f"C:\\ADB\\adb.exe exec-out screencap -p > {screenshot_path}")
    if (os.path.exists(screenshot_path)): #существует ли
        if (os.path.getsize(screenshot_path))>0: #не пустой
            img_rgb = cv2.imread(f'{work_dir}\\temp\\screenshot.png') #загружаем в память
            return True #возвращаем что получили удачно
        else:
            return False #возвращаем что получили битый
        
def recognize_screenshot(): #распознаем на скриншоте все известные целевые изображения
    global target_recognized, img_rgb
    printLog("recognize_screenshot started")
    for img_t in target_images: #перебираем целевые
        #ищем
        res = cv2.matchTemplate(img_rgb,target_images_rgb[img_t],cv2.TM_CCOEFF_NORMED)
        #получаем координаты и вероятности
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        #получаем координаты центра
        cx=max_loc[0]+target_images_psize[img_t][0]
        cy=max_loc[1]+target_images_psize[img_t][1]
        #записываем результаты
        target_recognized[img_t]=[True if (max_val>threshold) else False, cx, cy]
        #проверяем активна ли кнопка по цвету пикселя
        if img_t=='ad_enable' and target_recognized[img_t][0] and sum(img_rgb[cy][cx-158])<700 and sum(img_rgb[cy][cx+112])<500: 
            target_recognized[img_t][0]=False #если не активна, то исправляем найденное
            printLog(f"Img: ad_enable - disabled, location: x:{cx}, y:{cy}")
        #печатаем в лог все найденные
        if target_recognized[img_t][0]:
            printLog(f"Img: {img_t}, location: x:{cx}, y:{cy}")
    printLog("recognize_screenshot is complete.")

def tap_screen(x, y): #отправляем нажатие на экран в точке с x, y
    subprocess.run(['C:\\ADB\\adb.exe', 'shell', f'input tap {x} {y}'])
    printLog(f"tap x:{x}, y:{y}")

def au_worker(): #работник, принимающий решение что делать на основе найденных целевых картинок
    global discount_special_cn, start_time_ad, ad_mode, ruletka_mode
    if target_recognized['ad_enable'][0]: #если активна кнопка "смотреть"
            tap_screen(target_recognized['ad_enable'][1], target_recognized['ad_enable'][2]) #нажимаем
            start_time_ad = time.time()
            ad_mode=True
    elif target_recognized['ruletka'][0]: #если мы в рулетке
            if target_recognized['ruletka_attemp'][0]: #если видим кнопку для вращения
                tap_screen(target_recognized['ruletka_attemp'][1], target_recognized['ruletka_attemp'][2]) #нажимаем
                start_time_ad = time.time()
                ad_mode=True
            elif target_recognized['ruletka_end'][0]: #если больше нет попыток
                ruletka_mode=False #отмечаем режим недоступным
                printLog("Go menu")
                tap_screen(80, 1024) #выход в главное меню
    #первый тип акционного банера (при загрузке), закрываем
    elif (target_recognized['discount_banner0'][0] or target_recognized['discount_banner1'][0]) and target_recognized['main_menu_exit'][0]:
        tap_screen(target_recognized['main_menu_exit'][1], target_recognized['main_menu_exit'][2]) #закрываем
        ad_mode=False
    #второй тип акционного банера (при загрузке), закрываем
    elif target_recognized['discount_banner2'][0]:
        tap_screen(1764, 267) #закрываем
        ad_mode=False
    elif target_recognized['main_menu'][0]: #если в начальном меню, то
        if ruletka_mode: #еще не были в рулетке?
            printLog("Go ruletka")
            tap_screen(2070, 350) #идем в рулетку
        elif discount_special_cn<5: #уже были в специальном?
            printLog("Go special")
            tap_screen(190, 470) #идем в специальное
        else:
            printLog("Go box")
            tap_screen(62, 720) #идем в коробки
    elif target_recognized['box_open'][0]: #если можем открыть коробку
        printLog("Open box")
        tap_screen(652, 744) #открываем
        start_time_ad = time.time()
        ad_mode=True
    elif target_recognized['get'][0]: #если можем получить вознаграждение
        tap_screen(target_recognized['get'][1], target_recognized['get'][2])
        ad_mode=False
    elif target_recognized['ok'][0]: #подтверждаем получение вознаграждения
        tap_screen(target_recognized['ok'][1], target_recognized['ok'][2])
    elif target_recognized['discount_special'][0]: #если в специальном
        #если НЕ активна кнопка "смотреть"
        #нет для открытия коробок, то открываем следующую вкладку
        if discount_special_cn==1: 
            printLog("Go special 2")
            tap_screen(80, 370) #вторая вкладка
        elif discount_special_cn==2:
            printLog("Go special 3")
            tap_screen(80, 470) #третья вкладка
        elif discount_special_cn==3:
            printLog("Go special 4")
            tap_screen(80, 560) #четвертая вкладка
        elif discount_special_cn==4:
            printLog("Go menu")
            tap_screen(80, 1024) #выход в главное меню
        discount_special_cn+=1
    elif target_recognized['black_market'][0]: #если нельзя открыть бесплатно коробку (мы в меню коробок), то завершаем скрипт
        printLog("black_market closed")
        printLog("Go menu")
        tap_screen(80, 1024) #выход в главное меню
        printLog("Exit")
        sys.exit()  # завершаем программу
    elif target_recognized['back'][0] and target_recognized['bronze_box'][0]: #если покрутили рулетку, то
        printLog("Box exit")
        tap_screen(100, 1024) #выходим из коробки
        ad_mode=False
    else:
        tap_exit_ad=False
        for ad_e in {'ad_exit_next0', 'ad_exit_next1', 'ad_exit_next2', 'ad_exit0', 'ad_exit1', 'ad_exit2'}: #ищем кнопки для выхода из рекламы
            if target_recognized[ad_e][0]:
                tap_screen(target_recognized[ad_e][1], target_recognized[ad_e][2]) #выходим
                tap_exit_ad=True
                break
        if ad_mode and (not tap_exit_ad) and ((time.time() - start_time_ad)>timeout_ad): #если не нажимали на выход и время на рекламу вышло, а мы все еще в режиме просмотра
            printLog("timeout_ad")
            tap_screen(2200, 50) #жмем в ту область, где он должен быть


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
        printLog("End loop")
    printLog("Exit.")
