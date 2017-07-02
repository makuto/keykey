import mido
import time
import midiDevice


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


def testIO():
    # synthOutPort = chooseDevice(mido.get_output_names(), 'LMMS')
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
