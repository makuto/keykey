import mido
import time

"""
mido.get_input_names()
mido.get_output_names()
"""


def testOutput():
    outputs = mido.get_output_names()
    lmmsOutPort = None
    for output in outputs:
        if 'LMMS'.lower() in output.lower():
            lmmsOutPort = output

    if not lmmsOutPort:
        return

    with mido.open_output(lmmsOutPort) as lmmsOut:
        for i in range(1, 10):
            song = [100, 80, 40, 80, 100]
            for note in song:
                testNote = mido.Message(
                    'note_on', note=note, velocity=127, time=0.1)
                lmmsOut.send(testNote)
                testNote = mido.Message(
                    'note_on', note=20, velocity=127, time=0.1)
                lmmsOut.send(testNote)
                time.sleep(0.1)
                testNote = mido.Message('note_off', note=note,
                                        velocity=127, time=0.2)
                lmmsOut.send(testNote)
                testNote = mido.Message(
                    'note_off', note=20, velocity=127, time=0.2)
                lmmsOut.send(testNote)
                time.sleep(0.1)


def chooseDevice(devices, searchString):
    matchingDevice = None
    for device in devices:
        if searchString.lower() in device.lower():
            matchingDevice = device
    return matchingDevice


def testIO():
    #synthOutPort = chooseDevice(mido.get_output_names(), 'LMMS')
    synthOutPort = chooseDevice(mido.get_output_names(), 'OP-1')
    keyboardInPort = chooseDevice(mido.get_input_names(), 'CH345')

    if not synthOutPort or not keyboardInPort:
        return

    with mido.open_output(synthOutPort) as synthOut:
        with mido.open_input(keyboardInPort) as keyboardIn:
            while True:
                message = keyboardIn.receive()
                print(message)
                synthOut.send(message)


def simpleSequencer():
    #synthOutPort = chooseDevice(mido.get_output_names(), 'LMMS')
    synthOutPort = chooseDevice(mido.get_output_names(), 'OP-1')
    keyboardInPort = chooseDevice(mido.get_input_names(), 'CH345')

    if not synthOutPort or not keyboardInPort:
        return

    with mido.open_output(synthOutPort) as synthOut, mido.open_input(keyboardInPort) as keyboardIn:
        # 16th notes at 240 bpm should be fine
        frameRate = (60 / 240) / 4
        # Prevent the program from locking up if the frame rate gets too bad
        maximumCatchupTime = 0.25
        timeRoomForError = 0.0001
        sequence = []
        sequenceLastStartTime = 0.0
        sequenceTimeLength = 1.0
        sequenceLastNotePlayedTime = 0.0
        lastTime = time.time()
        timeAccumulated = 0.0
        try:
            while True:
                currentTime = time.time()
                sequenceTime = currentTime - sequenceLastStartTime
                frameDelta = currentTime - lastTime
                if frameDelta > maximumCatchupTime:
                    frameDelta = maximumCatchupTime
                lastTime = currentTime
                timeAccumulated += frameDelta

                print(frameDelta)

                while timeAccumulated >= frameRate:
                    print('Updated')

                    # Poll input
                    message = keyboardIn.poll()
                    while message:
                        print(message)
                        sequence.append((message, sequenceTime))
                        synthOut.send(message)
                        message = keyboardIn.poll()

                    # Play sequencer notes if it's time
                    # TODO: sort notes by time
                    for note in sequence:
                        # TODO: this comparison should have a margin of error equal
                        # to the frame rate
                        if note[1] <= sequenceTime and note[1] >= sequenceLastNotePlayedTime:
                            synthOut.send(note[0])
                            sequenceLastNotePlayedTime = max(sequenceLastNotePlayedTime, note[1])

                    # Restart sequence if necessary
                    if sequenceTime >= sequenceTimeLength:
                        sequenceLastStartTime = currentTime
                        sequenceLastNotePlayedTime = 0.0

                    timeAccumulated -= frameRate
                    timeAccumulated = max(0.0, timeAccumulated)

                sleepTime = frameRate - timeAccumulated - timeRoomForError
                if sleepTime > 0:
                    print('Sleep ' + str(sleepTime))
                    time.sleep(sleepTime)

        finally:
            print('Resetting synth due to exception')
            synthOut.reset()
            #synthOut.panic()

if __name__ == '__main__':
    # testOutput()
    # testIO()
    simpleSequencer()
