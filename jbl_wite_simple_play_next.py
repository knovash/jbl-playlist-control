import requests
import time

IP = "192.168.1.112"
PORT = "8080"
PIN = "1234"
ACTION_URL = "http://192.168.1.126:8010/cmd?action=toggle_music&player=jbl_wite"
NEXT_URL = "http://192.168.1.126:8010/cmd?action=next_channel&player=jbl_wite"
REFRESH_INTERVAL = 0.3  # Уменьшенный интервал для лучшего отслеживания
DOUBLE_CLICK_THRESHOLD = 2.0  # 2 секунды для двойного нажатия

# Глобальные переменные для отслеживания состояния
prev_volume = None
prev_status = "UNKNOWN"
first_run = True

# Переменные для отслеживания двойного нажатия
transition_start_time = 0
transition_stage = 0  # 0: ожидание, 1: OTHER→PLAYING, 2: PLAYING→OTHER

def get_value(node, tag):
    """Получение значения из API"""
    try:
        url = f"http://{IP}:{PORT}/fsapi/GET/{node}?pin={PIN}"
        response = requests.get(url, timeout=1)
        if response.status_code != 200:
            return None
        
        # Простой парсинг XML
        text = response.text
        start_tag = f"<{tag}>"
        end_tag = f"</{tag}>"
        start_idx = text.find(start_tag) + len(start_tag)
        end_idx = text.find(end_tag, start_idx)
        
        if start_idx >= 0 and end_idx >= 0:
            return text[start_idx:end_idx]
        return None
    except Exception:
        return None

def send_command(url):
    """Отправка команды на внешний сервер"""
    try:
        response = requests.get(url, timeout=0.5)
        return f"Command sent to {url.split('?')[0]}"
    except Exception as e:
        return f"Command failed: {str(e)}"

def handle_transitions(current_status, current_time):
    """Обработка переходов для двойного нажатия"""
    global transition_start_time, transition_stage
    
    # Сброс, если прошло слишком много времени
    if transition_stage > 0 and (current_time - transition_start_time) > DOUBLE_CLICK_THRESHOLD:
        transition_stage = 0
        return "Transition timed out"
    
    # Этап 1: OTHER → PLAYING
    if transition_stage == 0 and prev_status == "OTHER" and current_status == "PLAYING":
        transition_start_time = current_time
        transition_stage = 1
        return "Stage 1: OTHER → PLAYING"
    
    # Этап 2: PLAYING → OTHER
    if transition_stage == 1 and prev_status == "PLAYING" and current_status == "OTHER":
        transition_stage = 0
        return send_command(NEXT_URL)  # Двойное нажатие подтверждено
    
    return None

def main():
    global prev_volume, prev_status, first_run
    
    print("JBL Remote Controller - Ctrl+C to exit\n")
    print("Double click detection: OTHER → PLAYING → OTHER within 2 seconds")
    
    try:
        while True:
            current_time = time.time()
            
            # Получаем только необходимые значения
            volume = get_value("netRemote.sys.audio.volume", "u8")
            status_code = get_value("netRemote.play.status", "u8")
            
            # Преобразуем код статуса в читаемое значение
            status_map = {
                '0': 'STOPPED',
                '1': 'PAUSED',
                '3': 'PLAYING'
            }
            current_status = status_map.get(status_code, "OTHER")
            
            # Инициализируем предыдущие значения при первом запуске
            if first_run:
                prev_volume = volume
                prev_status = current_status
                first_run = False
                time.sleep(REFRESH_INTERVAL)
                continue
            
            # Обрабатываем события
            action_message = ""
            transition_message = ""
            double_click_message = ""
            
            # 1. Обработка переходов для двойного нажатия
            transition_result = handle_transitions(current_status, current_time)
            if transition_result:
                if "Command sent" in transition_result:
                    double_click_message = f"[Double Click] {transition_result}"
                else:
                    transition_message = f"[Transition] {transition_result}"
            
            # 2. Проверка условий для STOPPED состояния
            if current_status == "STOPPED":
                if volume != prev_volume:
                    action_message = send_command(ACTION_URL)
                elif prev_status != "STOPPED":
                    action_message = "Player transitioned to STOPPED"
            
            # Выводим текущий статус
            print(f"\n[Status] Volume: {volume}/20, Playback: {current_status}")
            
            # Выводим сообщения о действиях
            if transition_message:
                print(transition_message)
            if action_message:
                print(f"[Action] {action_message}")
            if double_click_message:
                print(double_click_message)
            
            # Обновляем предыдущие значения
            prev_volume = volume
            prev_status = current_status
            
            time.sleep(REFRESH_INTERVAL)
            
    except KeyboardInterrupt:
        print("\nMonitoring stopped")

if __name__ == "__main__":
    main()
