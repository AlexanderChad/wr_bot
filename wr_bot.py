import os
import subprocess
import sys
import time
import cv2
import numpy as np

show_screen_img = True

if show_screen_img:
    from PIL import Image, ImageTk
    import tkinter as tk

work_dir: str  # рабочая директория
screenshot_path: str  # пусть к скриншоту
img_rgb: np.ndarray  # скриншот
target_icons: np.ndarray = ['ad_enable', 'ruletka', 'ruletka_attemp', 'ruletka_end', 'get', 'ok', 'black_market', 'discount_special', 'box_open',
                            'main_menu', 'main_menu_exit', 'discount_banner0', 'discount_banner1', 'discount_banner2', 'discount_banner3', 'discount_banner3_exit', 'back', 'bronze_box',
                            'special_icon', 'ruletka_icon', 's1', 's2', 's3', 's4', 'gp', 'ch']
target_exit: np.ndarray = ['ad_exit_next0', 'ad_exit_next1', 'ad_exit_next2', 'ad_exit_next3', 'ad_exit_next4',
                           'ad_exit0', 'ad_exit1', 'ad_exit1_mask', 'ad_exit2', 'ad_exit3', 'ad_exit4', 'ad_exit5', 'ad_exit6', 'ad_exit7', 'ad_exit7_mask', 'ad_exit8', 'ad_exit9', 'ad_exit9_mask']
target_images: np.ndarray = np.concatenate([target_icons, target_exit])
# размеры квадрата справа для поиска кнопки выхода
target_exit_cut: np.ndarray = [700, 300]
target_images_rgb = {}  # загруженные целевые изображения
target_images_psize = {}  # половинный размеры загруженных целевых изображений
target_recognized = {}  # распознанные целевые изображения на скриншоте
threshold = 0.81  # порог распознавания
# пункты в меню специальных предложений
discount_special = [True, True, True, True]
start_time_ad: time  # время начала видео
timeout_ad = 90  # время, отведенное на рекламу
ad_mode = False  # режим просмотра рекламы
ruletka_mode = True  # режим рулетки, False - когда уже потратили все попытки


def printLog(str_log):  # лог в формате: время и информация
    print(time.strftime("%X\t", time.localtime()) + str_log)


def load_target_images():  # загружаем целевые картинки
    global target_images_rgb
    try:
        for img_t in target_images:  # перебираем
            target_images_rgb[img_t] = cv2.imread(
                f"{work_dir}\\images\\{img_t}.png")  # загружаем в память
            _, w, h = target_images_rgb[img_t].shape[::-1]  # получаем размеры
            target_images_psize[img_t] = [w//2, h//2]  # записываем половинные
    except:
        printLog("Err get img")
        sys.exit()  # завершаем программу


def get_screenshot():  # получаем с устройства скриншот, возвращаем результат получения
    global img_rgb
    printLog("get_screenshot started")
    try:
        img_raw = subprocess.run(['C:\\ADB\\adb.exe', 'exec-out', 'screencap',
                                 '-p'], stdout=subprocess.PIPE).stdout  # получаем файл
        img_arr = np.array(list(img_raw), 'uint8')  # декодируем в массив
        # считываем изображение
        img_rgb = cv2.imdecode(img_arr, cv2.IMREAD_COLOR)
        return True  # возвращаем что получили удачно
    except:
        return False  # возвращаем что получили битый


def recognize_screenshot():  # распознаем на скриншоте все известные целевые изображения
    global target_recognized, img_rgb
    printLog("recognize_screenshot started")
    for img_t in target_images:  # перебираем целевые
        # если маска, то пропускаем
        if '_mask' in img_t:
            continue
        img_cut_flag = False  # флаг, что распознаем только область
        if img_t in target_exit:  # это кнопка выхода?
            img_s = img_rgb[:target_exit_cut[1], -target_exit_cut[0]:]
            img_cut_flag = True
        else:
            img_s = img_rgb
        # ищем
        rec_metod = cv2.TM_SQDIFF_NORMED if img_t == 'ad_enable' else cv2.TM_CCOEFF_NORMED
        if img_t+'_mask' in target_images:
            res = cv2.matchTemplate(
                img_s, target_images_rgb[img_t], rec_metod, target_images_rgb[img_t+'_mask'])
        else:
            res = cv2.matchTemplate(
                img_s, target_images_rgb[img_t], rec_metod)
        # получаем координаты и вероятности
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        t_loc = min_loc if rec_metod == cv2.TM_SQDIFF_NORMED else max_loc
        # получаем координаты центра
        cx = t_loc[0]+target_images_psize[img_t][0]
        cy = t_loc[1]+target_images_psize[img_t][1]
        # если искали в области, то корректируем координаты
        if img_cut_flag:
            _, w, _ = img_rgb.shape
            cx += w-target_exit_cut[0]
        # записываем результаты
        target_recognized[img_t] = [
            True if ((max_val > threshold) if (rec_metod == cv2.TM_CCOEFF_NORMED) else (min_val < 0.003)) else False, cx, cy]
        # проверяем активна ли кнопка по цвету пикселя
        if img_t == 'ad_enable':
            print(f'sum(img_rgb[cy][cx+5]) = {sum(img_rgb[cy][cx+5])}, sum(img_rgb[cy][cx+10]) = {sum(img_rgb[cy][cx+10])}, min_val = {min_val}')
        if img_t == 'ad_enable' and target_recognized[img_t][0] and sum(img_rgb[cy][cx+5]) < 700 and sum(img_rgb[cy][cx+10]) < 500:
            # если не активна, то исправляем найденное
            target_recognized[img_t][0] = False
            printLog(f"Img: ad_enable - disabled, location: x:{cx}, y:{cy}")
        elif img_t == 'ad_exit2' and target_recognized[img_t][0] and img_rgb[cy+17][cx-18][0] < 150 and img_rgb[cy+17][cx-18][1] > 150 and img_rgb[cy+17][cx-18][2] > 200:
            # если не верная, то исправляем найденное
            target_recognized[img_t][0] = False
            print(f"Img: ad_exit2 - disabled, location: x:{cx}, y:{cy}")
        elif img_t == 'get' and target_recognized[img_t][0] and sum(img_rgb[cy][cx-1]) < 250:
            target_recognized[img_t][0] = False
            printLog(f"Img: get - disabled, location: x:{cx}, y:{cy}")
        # печатаем в лог все найденные
        if target_recognized[img_t][0]:
            printLog(f"Img: {img_t}, location: x:{cx}, y:{cy}")
            # если включено отображение на экране, то выделяем на картинке
            if show_screen_img:
                # draw the bounding box on the image
                cv2.rectangle(img_rgb, (t_loc[0], t_loc[1]), (t_loc[0]+target_images_psize[img_t]
                              [0]*2, t_loc[1]+target_images_psize[img_t][1]*2), (0, 255, 255), 3)
                cv2.putText(img_rgb, img_t, (t_loc[0]+target_images_psize[img_t]
                                             [0]*2, t_loc[1]+target_images_psize[img_t][1]*2), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 255, 255), 8)

    printLog("recognize_screenshot is complete.")


def tap_screen(x, y):  # отправляем нажатие на экран в точке с x, y
    subprocess.run(['C:\\ADB\\adb.exe', 'shell', f'input tap {x} {y}'])
    printLog(f"tap x:{x}, y:{y}")
    # если включено отображение на экране, то выделяем на картинке
    if show_screen_img:
        # draw the bounding box on the image
        cv2.circle(img_rgb, (x, y), 10, (0, 0, 255), 3)
        cv2.circle(img_rgb, (x, y), 20, (0, 0, 255), 3)
        cv2.circle(img_rgb, (x, y), 30, (0, 0, 255), 3)


def tap_screen_back():  # отправляем нажатие на кнопку "Назад"
    subprocess.run(['C:\\ADB\\adb.exe', 'shell', 'input keyevent 4'])
    printLog("tap ""Back""")


def au_worker():  # работник, принимающий решение что делать на основе найденных целевых картинок
    global discount_special, start_time_ad, ad_mode, ruletka_mode
    if target_recognized['get'][0]:  # если можем получить вознаграждение
        tap_screen(target_recognized['get'][1], target_recognized['get'][2])
        ad_mode = False
    elif target_recognized['ok'][0]:  # подтверждаем получение вознаграждения
        tap_screen(target_recognized['ok'][1], target_recognized['ok'][2])
    elif target_recognized['ad_enable'][0]:  # если активна кнопка "смотреть"
        tap_screen(target_recognized['ad_enable'][1],
                   target_recognized['ad_enable'][2])  # нажимаем
        start_time_ad = time.time()
        ad_mode = True
    # если нас выкинули на Google Play или Chrome
    elif target_recognized['gp'][0] or target_recognized['ch'][0]:
        tap_screen_back()  # возвращаемся назад
        ad_mode = False
    elif target_recognized['ruletka'][0]:  # если мы в рулетке
        if target_recognized['ruletka_attemp'][0]:  # если видим кнопку для вращения
            tap_screen(target_recognized['ruletka_attemp'][1],
                       target_recognized['ruletka_attemp'][2])  # нажимаем
            start_time_ad = time.time()
            ad_mode = True
        # если видим кнопку для ПЕРВОГО вращения
        elif target_recognized['get'][0]:
            tap_screen(target_recognized['get'][1],
                       target_recognized['get'][2])  # нажимаем
        elif target_recognized['ruletka_end'][0]:  # если больше нет попыток
            ruletka_mode = False  # отмечаем режим недоступным
            printLog("Go menu")
            tap_screen(target_recognized['back'][1], target_recognized['back'][2])  # выход в главное меню
    # единоразовое предложение, закрываем
    elif target_recognized['discount_banner3'][0] and target_recognized['discount_banner3_exit'][0]:
        tap_screen(target_recognized['discount_banner3_exit'][1],
                   target_recognized['discount_banner3_exit'][2])  # закрываем
        ad_mode = False
    # первый тип акционного банера (при загрузке), закрываем
    elif (target_recognized['discount_banner0'][0] or target_recognized['discount_banner1'][0]) and target_recognized['main_menu_exit'][0]:
        tap_screen(target_recognized['main_menu_exit'][1],
                   target_recognized['main_menu_exit'][2])  # закрываем
        ad_mode = False
    # второй тип акционного банера (при загрузке), закрываем
    elif target_recognized['discount_banner2'][0]:
        tap_screen(1764, 267)  # закрываем
        ad_mode = False
    elif target_recognized['main_menu'][0]:  # если в начальном меню, то
        # обнуляем информацию о вкладках в специальном
        discount_special = [True, True, True, True]
        # еще не были в рулетке?
        if ruletka_mode and target_recognized['ruletka_icon'][0]:
            printLog("Go ruletka")
            # идем в рулетку
            tap_screen(target_recognized['ruletka_icon']
                       [1], target_recognized['ruletka_icon'][2])
        # уже были в специальном? и можем пойти?
        elif any(discount_special) and target_recognized['special_icon'][0]:
            printLog("Go special")
            # идем в специальное
            tap_screen(target_recognized['special_icon']
                       [1], target_recognized['special_icon'][2])
        else:
            printLog("Go box")
            # tap_screen(62, 720) #идем в коробки
            printLog("Go menu")
            tap_screen(target_recognized['back'][1], target_recognized['back'][2])  # выход в главное меню
            printLog("Exit")
            sys.exit()  # завершаем программу
    elif target_recognized['box_open'][0]:  # если можем открыть коробку
        printLog("Open box")
        tap_screen(652, 744)  # открываем
        start_time_ad = time.time()
        ad_mode = True
    elif target_recognized['discount_special'][0]:  # если в специальном
        printLog("In special")
        # если НЕ активна кнопка "смотреть"
        # нет для открытия коробок, то открываем следующую вкладку
        if discount_special[0] and target_recognized['s1'][0]:
            discount_special[0] = False
            printLog("Go special 1")
            # первая вкладка
            tap_screen(target_recognized['s1'][1], target_recognized['s1'][2])
        elif discount_special[1] and target_recognized['s2'][0]:
            discount_special[1] = False
            printLog("Go special 2")
            # вторая вкладка
            tap_screen(target_recognized['s2'][1], target_recognized['s2'][2])
        elif discount_special[2] and target_recognized['s3'][0]:
            discount_special[2] = False
            printLog("Go special 3")
            # третья вкладка
            tap_screen(target_recognized['s3'][1], target_recognized['s3'][2])
        elif discount_special[3] and target_recognized['s4'][0]:
            discount_special[3] = False
            printLog("Go special 4")
            # четвертая вкладка
            tap_screen(target_recognized['s4'][1], target_recognized['s4'][2])
        else:
            printLog("Go menu")
            tap_screen(target_recognized['back'][1], target_recognized['back'][2])  # выход в главное меню
    # если покрутили рулетку, то
    elif target_recognized['back'][0] and target_recognized['bronze_box'][0]:
        printLog("Box exit")
        tap_screen(100, 1024)  # выходим из коробки
        ad_mode = False
    else:
        tap_exit_ad = False
        for ad_e in target_exit:  # ищем кнопки для выхода из рекламы
            # если маска, то пропускаем
            if '_mask' in ad_e:
                continue
            if target_recognized[ad_e][0]:
                tap_screen(target_recognized[ad_e][1],
                           target_recognized[ad_e][2])  # выходим
                tap_exit_ad = True
                break
        # если не нажимали на выход и время на рекламу вышло, а мы все еще в режиме просмотра
        if ad_mode and (not tap_exit_ad) and ((time.time() - start_time_ad) > timeout_ad):
            printLog("timeout_ad")
            tap_screen(2200, 50)  # жмем в ту область, где он должен быть


if __name__ == "__main__":
    printLog("Starting wr_bot")

    if show_screen_img:
        printLog("Init display")
        window = tk.Tk()

        def on_closing():
            destructor()

        window.protocol("WM_DELETE_WINDOW", on_closing)
        window.wm_title("Android screen")
        window.attributes('-fullscreen', False)
        window.bind("<F11>", lambda event: window.attributes(
            "-fullscreen", not window.attributes("-fullscreen")))
        window.bind("<Escape>", lambda event: destructor())
        # window.window = tk.Tk()  # Makes main window
        window.config(background="#FFFFFF")
        # Graphics window
        imageFrame = tk.Frame(window)
        imageFrame.grid(row=0, column=0, padx=0, pady=0)
        # Capture video frames
        lmain = tk.Label(imageFrame)
        lmain.grid(row=0, column=0)

        def destructor():
            cv2.destroyAllWindows()  # it is not mandatory in this application
            sys.exit()

        def show_frame():
            global img_rgb
            cap_img = Image.fromarray(img_rgb)
            ciw, cih = cap_img.size
            cap_img_arr = np.array(cap_img.resize((ciw//2, cih//2), Image.ANTIALIAS))
            cv2image = cv2.cvtColor(cap_img_arr, cv2.COLOR_BGR2RGBA)
            imgtk = ImageTk.PhotoImage(image=Image.fromarray(cv2image))
            lmain.imgtk = imgtk
            lmain.configure(image=imgtk)

        def upd_img_on_window():
            show_frame()  # Display
            window.update()

    work_dir = os.path.abspath(os.path.dirname(sys.argv[0]))
    screenshot_path = f'{work_dir}\\temp\\screenshot.png'
    printLog(f'Running from: {work_dir}')

    printLog("Loading target images...")
    load_target_images()
    printLog("Loading is complete.")

    ret = subprocess.run(['C:\\ADB\\adb.exe', 'devices'],
                         capture_output=True, text=True).stdout
    printLog(f'Devices: {ret}')

    while (1):
        printLog("Loop")
        if get_screenshot():  # пытаемся получить скриншот, если получили
            if show_screen_img:
                upd_img_on_window()
            recognize_screenshot()  # распознаем все что знаем
            if show_screen_img:
                upd_img_on_window()
            au_worker()  # принимаем действия
            if show_screen_img:
                upd_img_on_window()
            # после выполнения действий даем время на анимацию (загрузку активити)
        time.sleep(1)
        printLog("End loop")
    printLog("Exit.")
