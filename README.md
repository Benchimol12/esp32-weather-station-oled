# 🌦️ Estação Meteorológica ESP32 com Interface OLED

Dispositivo autónomo baseado em ESP32 que apresenta condições meteorógicas em tempo real 
e previsão horária, consumindo a API Open-Meteo, com UI gráfica customizada em display SSD1306.

## 🎯 Destaques Técnicos
- **Event Loop não-bloqueante:** Implementação própria de scheduler cooperativo com 
  `ticks_ms()/ticks_diff()`, permitindo resposta ao botão físico durante animações longas.
- **Otimização de Heap:** Escolha deliberada de HTTP sobre HTTPS e parsing JSON sequencial 
  para operar dentro dos limites de RAM do ESP32 sem crash por fragmentação.
- **Motor de Renderização Gráfica:** Ícones meteorológicos procedurais (vetor de vento 
  rotacionado conforme direção) e blitting de sprites via `framebuf`.
- **Resiliência:** Retries com backoff para WiFi/NTP e degradação graciosa quando a API falha.

## 🧠 Decisões de Engenharia (Trade-offs)
| Decisão | Justificação |
|---------|--------------|
| HTTP em vez de HTTPS | TLS consome ~40KB de heap; risco de MemoryError em requests consecutivos |
| API Open-Meteo | Sem API key necessária, elimina gestão de segredos no dispositivo |
| Polling vs Interrupts | Polling com debounce software suficiente para UX de menu humano |

## 🛠️ Stack
ESP32 · MicroPython · I2C/OLED SSD1306 · framebuf · urequests/ujson · NTP · DHT11
