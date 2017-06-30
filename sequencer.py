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
		        testNote = mido.Message('note_on', note=note, velocity=127, time=0.1)
		        lmmsOut.send(testNote)
		        testNote = mido.Message('note_on', note=20, velocity=127, time=0.1)
		        lmmsOut.send(testNote)
		        time.sleep(0.1)
		        testNote = mido.Message('note_off', note=note, velocity=127, time=0.2)
		        lmmsOut.send(testNote)
		        testNote = mido.Message('note_off', note=20, velocity=127, time=0.2)
		        lmmsOut.send(testNote)
		        time.sleep(0.1)


if __name__ == '__main__':
    testOutput()
