from machine import Pin
import utime
import select
import sys
import machine


def main():

    # GPIO settings
    ENABLE_PIN = 13
    PULSE_PIN = 14
    DIRECTION_PIN = 15
    PHOTOMULTIPLIER_PIN = 16
    LIMIT_SWITCH_START_PIN = 17
    LIMIT_SWITCH_END_PIN = 18

    # Linear actuator settings
    ENABLE = Pin(ENABLE_PIN, Pin.OUT)
    PULSE = Pin(PULSE_PIN, Pin.OUT)
    DIRECTION = Pin(DIRECTION_PIN, Pin.OUT)

    # Photomultiplier and limit switches settings
    PHOTOMULTIPLIER = Pin(PHOTOMULTIPLIER_PIN, Pin.IN)
    LIMIT_SWITCH_START = Pin(LIMIT_SWITCH_START_PIN, Pin.IN, Pin.PULL_UP)
    LIMIT_SWITCH_END = Pin(LIMIT_SWITCH_END_PIN, Pin.IN, Pin.PULL_UP)

    # Serial reading through USB
    poll_obj = select.poll()
    poll_obj.register(sys.stdin, 1)

    while True:
        # Verify data in sys.stdin 
        if poll_obj.poll(0):
            # Reads a sys.stdin line
            adquisition = sys.stdin.readline().strip()
            batch, operator, distance, adquisition_time=adquisition.split(',')
            break
        
        utime.sleep(0.1)



    # Variables
    STEP_DELAY = 0.001  # 1 ms between stepper pulses
    STEPS_PER_MM = 200  # Stepper pulses per mm
    MAX_POSITION=int(distance) # Scanning distance
    MEASUREMENT_TIME=int(adquisition_time)*60/(MAX_POSITION*2)


    # Stepper motor control
    def step_motor(steps, direction, delay=STEP_DELAY):
        DIRECTION.value(direction)
        for _ in range(steps):
            # Limit switches check
            if direction and LIMIT_SWITCH_END.value():
                print('end')
                while not LIMIT_SWITCH_START.value():
                    step_motor(STEPS_PER_MM, False)
                ENABLE.value(1)
                main()
            elif not direction and LIMIT_SWITCH_START.value():
                break
            
            PULSE.value(1)
            utime.sleep(delay)
            PULSE.value(0)
            utime.sleep(delay)

    # Enables stepper
    ENABLE.value(0)  

    # Photomultiplier reading
    def measure_pulses(duration):
        start_time = utime.ticks_ms()
        pulse_count = 0
        while utime.ticks_diff(utime.ticks_ms(), start_time) < duration * 1000:
            if PHOTOMULTIPLIER.value():
                pulse_count += 1
                while PHOTOMULTIPLIER.value():  # Waits until pulse ends
                    pass
        return pulse_count

    # Main cycle
    try:
        # Returns to origin
        while not LIMIT_SWITCH_START.value():
            step_motor(STEPS_PER_MM, False)

        # 0,5mm steps scanning
        for position in [i*0.5 for i in range(0,int((MAX_POSITION+0.5)*2))]:
            pulses = measure_pulses(MEASUREMENT_TIME)
            print(f"{int(position*10)};",f"{pulses}")
            if position < MAX_POSITION:
                move_step = STEPS_PER_MM / 2
                step_motor(move_step, True) 

        # Returns to origin
        print('end')
        while not LIMIT_SWITCH_START.value():
            step_motor(STEPS_PER_MM, False)
        ENABLE.value(1)  # Disables stepper
        

    except Exception as e:
        print(f"Error: {e}")


while True:
    main()
