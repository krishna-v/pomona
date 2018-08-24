# Pomona - Power Monitor Appliance
Pomona is a Raspberry Pi based appliance that monitors power outages and can shut down remote machines (currently only Linux) with configurable delay times. 
## Hardware Components
- Raspberry Pi. Any model with network connectivity should do, but the Zeros will need headers to be soldered. I used a [first generation Model B.](https://www.sparkfun.com/products/retired/11546)
- Relay board to trigger the Pi on loss of power. I happened to already have [this one](https://www.amazon.in/Generic-Channel-Relay-Module-Electronic/dp/B00C59NOHK) with me. Only a single relay is required.
- Power adapter to trigger the relay, connected to raw electric power. I used an old USB wall wart from a Nook.
    - USB cable - I salvaged one from a dead mouse. It had jumper connectors already crimped on the end which I could plug onto the relay board pins.
- 2 Jumpers wires to connect the relay with the Pi. Female plug on one side to connect to the GPIO pins and either bare wire or male pin to connect to the relay outputs.
- A box to put everything in - I used an old cardboard box from a smartphone and made cutouts where needed.
## Software Components
- Raspbian - Other flavours of Linux on the Pi would probably work as well.
- Python 3.5+
- python modules: python3-gpiozero and python3-daemon
## Hardware Assembly
- Connect the Normally open (NO) outputs of the relay to a GPIO pin and a ground pin of the Pi. When the relay engages, the GPIO pin should be pulled low. I used pin 3, but you can use any GPIO pin and configure the .ini file accordingly.
- connect the USB cable to the relay, so that the relay engages when USB power is applied.
- Plug the Pi power source to UPS power, and the relay power source to raw electric supply.
- Plug the Pi into your wired network if you are using ethernet.

Thats it! Your hardware should be ready.
## Software setup
- log in to the Pi and ensure network connectivity.
- `sudo apt-get install python3-gpiozero python3-daemon`
- download the pomona python files and the sample ini file.
- Customize the .ini file for your setup.
- start pomona in the foreground using `sudo python3 pomona.py -c <ini file> -F -v -w`
- Test your setup by toggling power to the relay power supply. You should see appropriate log messages in the daemon log file (usually /var/log/daemon.log)
- You should be able toi see Pomona's event log on its webpage as well. (default: http://<machinename>:8000)
- Generate an RSA key-pair for Pomona by following [these steps](https://help.ubuntu.com/community/SSH/OpenSSH/Keys)
  - Use a different filename instead of id_rsa for Pomona, as normally only Pomona should be using this key-pair to log in to remote systems. I used id_pomona
  - Don't set a passphrase on the key-file. Currently passphrase protected key files are not supported.
- Edit the .ini file to point to the key file you created.
- Create User IDs for Pomona on the remote machines you wish to control, and transfer the keys to the remote machines using `ssh-copy-id`
- Test that you can ssh login to the remote machines without passwords and using the transferred key. (`ssh -i <key file> user@machine`)
- Disable password login on the remote machine using `passwd -l user` [(Reference)](https://www.cyberciti.biz/faq/linux-locking-an-account/)
- Edit the ini file to manage the remote hosts as per your requirements.

You should be all set at this point!
Final step: Add Pomona to rc.local by adding the line:
`python3 <path to pomona.py> -c <path to ini file> -w`

