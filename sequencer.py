import mido
import time
import curses
import midiDevice

# If true, no console output will be shown (for performance)
headless = False


def cursesRingPrint(stdscr, stringToPrint):
    if not headless:
        stdscr.addstr(stringToPrint)
        stdscr.clrtoeol()

        cursorPos = curses.getsyx()
        newPos = [cursorPos[0] + 1, cursorPos[1]]
        screenHeightWidth = stdscr.getmaxyx()
        if newPos[0] > screenHeightWidth[0] - 1:
            newPos[0] = 1

        stdscr.move(newPos[0], newPos[1])


def simpleSequencer(stdscr):
    debugTiming = False

    if not headless:
        # Make getch() nonblocking
        stdscr.nodelay(1)

        stdscr.addstr("Current mode: Simple Sequencer", curses.A_REVERSE)
        stdscr.move(1, 0)
        stdscr.refresh()

    with midiDevice.openOut('OP-1') as synthOut, midiDevice.openIn('CH345') as keyboardIn:
        if not synthOut or not keyboardIn:
            return

        # 16th notes at 240 bpm should be fine
        frameRate = (60 / 240) / 4
        # Prevent the program from locking up if the frame rate gets too bad
        maximumCatchupTime = 0.25

        timeRoomForError = 0.0001

        # Start with a click
        sequence = [(mido.Message(
                    'note_on', note=60, velocity=64, time=0.0), 0.0), (mido.Message(
                        'note_off', note=60, velocity=127, time=0.1), 0.1)]
        sequenceLastStartTime = 0.0
        sequenceTimeLength = 3.0
        sequenceLastNotePlayedTime = 0.0
        sequenceFirstStartTime = 0.0
        sequenceDriftStartTime = 0.0
        sequenceNumTimesPlayed = 0
        sequenceNumTimesMeasureDrift = 4

        isRecording = False

        lastTime = time.time()
        timeAccumulated = 0.0
        shouldQuit = False
        try:
            while True:
                if not headless:
                    stdscr.refresh()

                currentTime = time.time()
                sequenceTime = currentTime - sequenceLastStartTime
                frameDelta = currentTime - lastTime
                if frameDelta > maximumCatchupTime:
                    frameDelta = maximumCatchupTime
                lastTime = currentTime
                timeAccumulated += frameDelta

                if debugTiming:
                    cursesRingPrint(stdscr, str(frameDelta))

                while timeAccumulated >= frameRate:
                    if debugTiming:
                        cursesRingPrint(stdscr, 'Updated')

                    # Poll MIDI input
                    message = keyboardIn.poll()
                    while message:
                        cursesRingPrint(stdscr, str(message))

                        if isRecording:
                            sequence.append((message, sequenceTime))
                        synthOut.send(message)

                        message = keyboardIn.poll()

                    # Poll keyboard input
                    inputChar = stdscr.getch()
                    if inputChar == ord('q'):
                        shouldQuit = True
                        break
                    elif inputChar == ord('f'):
                        cursesRingPrint(stdscr, "This is a test")
                    elif inputChar == ord('r'):
                        isRecording = not isRecording
                        cursesRingPrint(
                            stdscr, 'Recording' if isRecording else 'Stopped recording')

                    # Play sequencer notes if it's time
                    # TODO: sort notes by time, out messages work strangely
                    for note in sequence:
                        # TODO: this comparison should have a margin of error equal
                        # to the frame rate
                        if note[1] <= sequenceTime and note[1] >= sequenceLastNotePlayedTime:
                            synthOut.send(note[0])
                            sequenceLastNotePlayedTime = max(
                                sequenceLastNotePlayedTime, note[1])

                            if not sequenceFirstStartTime:
                                sequenceFirstStartTime = currentTime

                    # Restart sequence if necessary
                    if sequenceTime >= sequenceTimeLength:
                        # TODO: Minimize drift over time
                        if sequenceNumTimesPlayed % sequenceNumTimesMeasureDrift == 0:
                            cursesRingPrint(stdscr, 'Sequence played ' + str(sequenceNumTimesPlayed)
                                            + ' times; drifted ' +
                                            str((currentTime - sequenceFirstStartTime)
                                                - (sequenceTimeLength * sequenceNumTimesPlayed)) + ', drifted '
                                            + str((currentTime - sequenceDriftStartTime)
                                                  - (sequenceTimeLength * sequenceNumTimesMeasureDrift))
                                            + ' this ' + str(sequenceNumTimesMeasureDrift) + ' drift frame')
                            sequenceDriftStartTime = currentTime

                        sequenceLastStartTime = currentTime
                        sequenceLastNotePlayedTime = 0.0
                        sequenceNumTimesPlayed += 1

                    timeAccumulated -= frameRate
                    timeAccumulated = max(0.0, timeAccumulated)

                if shouldQuit:
                    break

                sleepTime = frameRate - timeAccumulated - timeRoomForError
                if sleepTime > 0:
                    if debugTiming:
                        cursesRingPrint(stdscr,
                                        'Sleep ' + str(sleepTime))
                    time.sleep(sleepTime)

        finally:
            cursesRingPrint(stdscr,
                            'Resetting synth due to exception')

            synthOut.reset()
            """ Sometimes notes hang because a note_off has not been sent. To (abruptly) stop all sounding
                 notes, you can call:
                    outport.panic()
                This will not reset controllers. Unlike reset(), the notes will not be turned off
                 gracefully, but will stop immediately with no regard to decay time.
                http://mido.readthedocs.io/en/latest/ports.html?highlight=reset """
            synthOut.panic()

# Note that key repeats mean that key holding is fucking weird


def testKeyInput(stdscr):
    # Make getch() nonblocking
    stdscr.nodelay(1)
    while True:
        inputChar = stdscr.getch()
        if inputChar == ord('f'):
            stdscr.addstr("This is a test")
        elif inputChar == ord('q'):
            break

        time.sleep(0.05)


def main():
    if headless:
        simpleSequencer(None)
    else:
        curses.wrapper(simpleSequencer)

if __name__ == '__main__':
    main()
