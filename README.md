# sysinfo

Dieses Repository stellt eine kleine Flask-Webanwendung bereit, die Systeminformationen grafisch aufbereitet anzeigt. Die Speicherauslastung und Festplattenbelegung werden dabei als Fortschrittsbalken dargestellt. Zusätzlich gibt es ein Shell-Skript, das die gleichen Informationen in der Konsole ausgibt. Beide Varianten können optional einen Geschwindigkeitstest des Netzwerks ausführen.

## Voraussetzungen

Python 3 und pip müssen installiert sein. Anschließend Flask sowie speedtest-cli installieren:

```bash
pip install Flask speedtest-cli
```

## Starten der Webanwendung

```bash
python app.py
```

Danach im Browser <http://localhost:8015> aufrufen.

## Alternativ: Skript in der Konsole

```bash
bash sysinfo.sh
```

Das Skript gibt Informationen zu Betriebssystem, Distribution, CPU, Arbeitsspeicher, Festplattenbelegung und Netzwerkadressen aus.
Ist `speedtest-cli` vorhanden, wird nacheinander versucht, mehrere deutsche Server zu nutzen (z.B. `68177`, `60421`, `59653`, `64665` und `68164`).
Schlagen alle fehl, erfolgt ein weiterer Versuch ohne Vorgabe eines Servers. Erst wenn auch dieser scheitert, wird ersatzweise ein Ping-Test ausgeführt.
