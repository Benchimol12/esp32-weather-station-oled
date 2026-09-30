#### ======Mix 1=================   
from machine import Pin, PWM, SoftI2C
from time import sleep, sleep_ms, ticks_ms, ticks_diff
import network
import gc
from dht import DHT11
from secret import WIFI_SSID, WIFI_PASSWORD
from modulos import ssd1306, animate
from modulos.roboeyes import *
from modulos.roboeyes import RoboEyes
from ntptime import settime, gmtime
import urequests
import ujson
gc.collect()
sleep(0.5)
##### Configuração inicial e de pinos   

##LED embutido na placa PCB
pwm_led = PWM(Pin(25), freq=1000)  # PWM em GPIO 25
pwm_led.init()

## Ecrã OLED
i2c = SoftI2C(scl=Pin(4), sda=Pin(18), freq=400000)
oled_width = 128
oled_height = 32 # 25 é a altura maxima utilizavel antes de perder parte do texto ou desenho
oled = ssd1306.SSD1306_I2C(oled_width, oled_height, i2c)

## Botão embutido na placa PCB
button_pressed = Pin(15, Pin.IN, Pin.WAKE_HIGH) #Pin only goes high when pressed, to troubleshoot #help(Pin(15, Pin.IN))

## Inicializa sensor Temp e Humi no GPIO 36
dht = DHT11(Pin(13, Pin.IN))

## Dados para comunicação com a API do open-meteo
# Usado "http://" em vez de "https: //" para evitar erros de alocação de memoria causadas durante o pedido
LAT = 41.1671 #Aldoar, Porto
LON = -8.6691
URL = (
    "http://api.open-meteo.com/v1/forecast"
    f"?latitude={LAT}&longitude={LON}"
    "&hourly=apparent_temperature"
    "&hourly=cloud_cover"
    "&hourly=wind_speed_10m"
    "&hourly=wind_direction_10m"
    "&hourly=weather_code"
    "&timezone=auto"
    "&forecast_hours=3"
    "&forecast_days=1"
)

## Menu
num_menu = 0
def next_menu(n_menu):
    global num_menu
    if n_menu == 4:
        clean_oled()
        num_menu = 0
    else:
        num_menu += 1
            
def clean_oled():
    ## Limpeza do ecrã OLED
    oled.fill(0)
    oled.show()

def wifi_connect(timeout_s=10):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if wlan.isconnected():
        print("WiFi conectado: ", wlan.ifconfig())
        return wlan

    print("Conectando ao WiFi...")
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)

    t0 = ticks_ms()
    while not wlan.isconnected():
        if ticks_diff(ticks_ms(), t0) > timeout_s * 1000:
            raise OSError("WiFi timeout")
        sleep(0.25)

    print("WiFi conectado:", wlan.ifconfig())
    return wlan


def set_time(retries=3, pause_s=2):
    for attempt in range(1, retries + 1):
        try:
            print("Sincronizando hora... tentativa ", attempt)
            settime()
            timezone_offset = 1 #horario veraõ
            ## define o formato da data e hora
            global data, dia, mes, ano, hora
            data = gmtime()
            dia = data[2]
            mes = data[1]
            ano = data[0]
            hora = data[3] + timezone_offset #horario veraõ
            #controle da transição de um dia para o outro
            if hora == 24:
                dia += 1
                hora = 0
                if dia == 32 and mes in [1, 3, 5, 7, 8, 10, 12]:
                    dia = 1
                    mes += 1
                    if mes == 13:
                        mes = 1
                        ano += 1
                elif dia == 31  and mes in [4, 6, 9, 11]:
                    dia = 1
                    mes += 1
                elif dia == 29 and mes == 2:
                    dia = 1
                    mes += 1
            print("Hora sincronizada:", data)
            return True
        except OSError as e:
            print("Erro ao sincronizar hora:", e)
            clean_oled()
            oled.text("Erro ao sincronizar", 0, 8)
            oled.text(f"hora: {e}", 0, 25)
            oled.show()
            if attempt < retries:
                sleep(pause_s)
        except Exception as e:
            print("Erro inesperado ao sincronizar hora:", e)
            clean_oled()
            oled.text("Erro inesperado ao", 0, 1)
            oled.text("sincronizar hora:", 0, 13)
            oled.text(f"{e}", 0, 20)
            oled.show()
            if attempt < retries:
                sleep(pause_s)

    return False

def wifi_reset():
    ## Reseta completamente a rede WiFi
    wlan = network.WLAN(network.STA_IF)
    wlan.active(False)
    sleep(0.05)
    wlan.active(True)

def get_weather():
    ## Chamada e obtenção da temperatura no API: "https://api.open-meteo.com/v1/forecast". Mais informações ### Configuração inicial e de pinos
    try:
        r = urequests.get(URL)
        data = r.json()
        r.close()
        return data
    except Exception as e:
        print("Erro com o API do open-meteo:", e)
        clean_oled()
        oled.text("Erro com o open-meteo", 0, 8)
        oled.text(f"{e}", 0, 25)
        oled.show()
        sleep(2.5)
    finally: #Limpa a memoria de forma a evitar erros de alocação de memoria
        gc.collect()
        sleep(0.25)
    
## Executa uma função por um tempo em milisegundos
def executar_por_tempo(funcao, tempo: int, num_menu= 0, sucesso= 0, passo_ms=50):
    t_ant = ticks_ms()
    while True:
        t_atual = ticks_ms()
        if isinstance(funcao, (list, tuple)):
            for item in range(len(funcao)):
                funcao[item]
        else: funcao
        # Sai por tempo
        if ticks_diff(t_atual, t_ant) >= tempo:
            break
        # Sai por botão
        if button_pressed.value() == 1:
            if sucesso == 0:
                next_menu(num_menu)
            break
        sleep_ms(passo_ms)

## Loop principal com reconexão automática 
reconnect_count = 0
pause_menu = 0
while True:  
    clean_oled() #Inicializa o ecrã oled sempre com tela preta
    try:
        ## Conecta WiFi
        wlan = wifi_connect(timeout_s=15)
        if not wlan.isconnected():
            continue
        ## Define a hora atual
        if not set_time(retries=3, pause_s=2):
            print("Hora não sincronizada. Tentando novamente...")
            continue

        ## Libera memória
        gc.collect()
        print("Memória livre:", gc.mem_free(), "bytes")
        sleep(0.75) #Aguarda um pouco para estabilizar
        
        ## Mostra no ecrã OLED e apaga o LED embutido na placa indicando que já pode ser usada
        pwm_led.duty(0)
        funcoes = [oled.framebuf.rect(0, 0, 127, 31, 1), oled.text("sucesso!", 32, 12), oled.show()] #Cada caractere tem a dimensão de 8x8 pixels
        executar_por_tempo(funcoes, 5000, sucesso = 1)    
            
        ## Loop de mensagem
        while True:
            clean_oled()
            try:
                
                if button_pressed.value() == 1:
                    if num_menu == 0 and pause_menu == 1: #Pausa/Fim de menu
                        sleep(0.5)
                        pause_menu = 0
                        continue
                        
                    elif num_menu == 0 and pause_menu == 0: #Entrada no modo de Espera
                        next_menu(num_menu)
                        continue
                    
                    elif num_menu == 1: #Animaçaõ de olhos
                        sleep(0.3) #Garante que a animação não é saltada devido ao tempo que o usuario levou com o botão pressionado por motivos mecanicos
                        repetition_menu_1 = 0
                        while num_menu == 1 and repetition_menu_1 <= 3:
                            executar_por_tempo(animate.open(), 200, num_menu)
                            if num_menu != 1: break
                            
                            executar_por_tempo(animate.blink_animation(), 300, num_menu)
                            if num_menu != 1: break
                            
                            executar_por_tempo(animate.look_left(), 500, num_menu)
                            if num_menu != 1: break
                            
                            executar_por_tempo(animate.look_right(), 500, num_menu)
                            if num_menu != 1: break
                            
                            executar_por_tempo(animate.look_down(), 500, num_menu)
                            if num_menu != 1: break
                            
                            executar_por_tempo(animate.look_up(), 500, num_menu)
                            if num_menu != 1: break
                            
                            repetition_menu_1 += 1
                            if repetition_menu_1 == 3: num_menu = 0
                            
                    elif num_menu == 2: #Data e Hora
                        sleep(0.3) #Garante que o menu não é saltado
                        #dht.measure()
                        #temperatura = dht.temperature()
                        #humidade = dht.humidity()
                        repetition_menu_2 = 0
                        menu_2_max = 10 #Mostra durante 10 segundos
                        while num_menu == 2 and repetition_menu_2 <= menu_2_max: 
                            data = gmtime()
                            ## Garanties that the "minuto" always have 2 digits
                            if len(str(data[4])) == 1: minuto = f"0{data[4]}"
                            else: minuto = data[4]
                            ## Garanties that the "segundo" always have 2 digits
                            if len(str(data[5])) == 1: segundo = f"0{data[5]}"    
                            else: segundo = data[5]
                            # draw a rectangle outline 10,10 to 107,43, colour=1
                            funcoes = [oled.framebuf.rect(0, 0, 127, 31, 1), oled.text(f"Data: {dia}/{mes}/{ano}", 3, 5), oled.text(f"Hora: {hora}:{minuto}:{segundo}", 6, 17), oled.show()]
                            executar_por_tempo(funcoes, 900, num_menu)
                                
                            if repetition_menu_2 == menu_2_max or button_pressed.value() == 1:
                                if repetition_menu_2 == menu_2_max:
                                    num_menu = 0
                                clean_oled()
                                break
                            repetition_menu_2 += 1
                            clean_oled()
                    
                    elif num_menu == 3: #Weather
                        sleep(0.3)
                        
                        fb = animate.display_logo()
                        funcoes = [oled.framebuf.blit(fb, 56, 0), oled.show()]
                        weather = get_weather()
                        clean_oled()
                        
                        temp = weather['hourly']['apparent_temperature'][0]
                        wind_speed = weather['hourly']['wind_speed_10m'][0]
                        wind_deg = weather['hourly']['wind_direction_10m'][0]
                        weather_code = weather['hourly']['weather_code'][0]
                        cloud = weather['hourly']['cloud_cover'][0]
                        
                        data_e_hora_2 = weather['hourly']['time'][1].lstrip(f"{ano}-{mes}-{dia}")
                        hora_2 = data_e_hora_2.lstrip("T")
                        temp_2 = weather['hourly']['apparent_temperature'][1]
                        wind_speed_2 = weather['hourly']['wind_speed_10m'][1]
                        wind_deg_2 = weather['hourly']['wind_direction_10m'][1]
                        weather_code_2 = weather['hourly']['weather_code'][1]
                        
                        data_e_hora_3 = weather['hourly']['time'][2].lstrip(f"{ano}-{mes}-{dia}")
                        hora_3 = data_e_hora_3.lstrip("T")
                        temp_3 = weather['hourly']['apparent_temperature'][2]
                        wind_speed_3 = weather['hourly']['wind_speed_10m'][2]
                        wind_deg_3 = weather['hourly']['wind_direction_10m'][2]
                        weather_code_3 = weather['hourly']['weather_code'][2]
                        
                        print(weather_code)
                        print(weather_code_2)
                        print(weather_code_3)
                        
                        funcoes = [oled.text("Aldoar, Porto", 16, 0), animate.draw_wind_icon(oled, wind_deg, 114, 13), animate.draw_weather_icon(oled, weather_code, 0, 7), oled.text("T:" + str(round(temp)) + "C", 6, 25), oled.text(str(round(wind_speed)) + "km/h", 60, 18), oled.text(str(cloud) + "%", 19, 11), oled.show()]
                        executar_por_tempo(funcoes, 30000, num_menu)
                        
                    elif num_menu == 4: #Weather por Hora
                        sleep(0.3)
                        
                        funcoes = [animate.draw_weather_icon(oled, weather_code_2, 0, 6), oled.text(hora_2, 18, 0), oled.text(str(round(temp_2)) + "C", 25, 12), oled.text(str(round(wind_speed_2)) + "km/h", 4, 24),animate.draw_weather_icon(oled, weather_code_3, 64, 6), oled.text(hora_3, 82, 0),  oled.text(str(round(temp_3)) + "C", 89, 12), oled.text(str(round(wind_speed_3)) + "km/h", 68, 24), oled.show()]
                        executar_por_tempo(funcoes, 30000, num_menu)
                            
            except Exception as e:
                print(f"Erro no check_msg: {e}")
                clean_oled()
                oled.text("Erro no check_msg:", 0, 10)
                oled.text(f"{e}", 0, 25)
                oled.show()
                sleep(2.5)
                break

    except OSError as e:
        print(f"Erro OSError: {e}")
        clean_oled()
        oled.text("Erro OSError:", 0, 10)
        oled.text(f"{e}", 0, 25)
        oled.show()
        sleep(2.5)
    except Exception as e:
        print(f"Erro geral: {e}")
        clean_oled()
        oled.text("Erro geral:", 0, 10)
        oled.text(f"{e}", 0, 25)
        oled.show()
        sleep(2.5)
