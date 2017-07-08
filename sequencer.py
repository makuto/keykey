import mido
import time
import curses
import midiDevice
import math

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
        stdscr.refresh()


def manualNoteResetCH345(output):
    ch345KeyboardRange = [53, 84]
    for note in range(ch345KeyboardRange[0], ch345KeyboardRange[1] + 1):
        noteOffMessage = mido.Message(
            'note_on', note=note, velocity=0, time=0.0)
        output.send(noteOffMessage)


def simpleSequencer(stdscr):
    debugTiming = False

    if not headless:
        # Make getch() nonblocking
        stdscr.nodelay(1)

        stdscr.addstr("KeyKey --- Current mode: Simple Sequencer",
                      curses.A_REVERSE)
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
        sequenceTimeLength = 1.0
        sequenceLastNotePlayedTime = 0.0
        sequenceFirstStartTime = 0.0
        sequenceDriftStartTime = 0.0
        sequenceNumTimesPlayed = 0
        sequenceNumTimesMeasureDrift = 4

        isRecording = False
        isPlayback = True

        lastTime = time.time()
        timeAccumulated = 0.0
        shouldQuit = False
        try:
            while True:
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
                    # [Q]uit
                    if inputChar == ord('q'):
                        shouldQuit = True
                        break
                    # Toggle [P]layback
                    elif inputChar == ord('p'):
                        isPlayback = not isPlayback
                        cursesRingPrint(
                            stdscr, 'Playback' if isPlayback else 'Stopped Playback')
                        if not isPlayback:
                            isRecording = False
                    # [C]lear sequence
                    elif inputChar == ord('c'):
                        sequence = []
                        cursesRingPrint(stdscr, "Cleared sequence")
                    # [R]ecord
                    elif inputChar == ord('r'):
                        isRecording = not isRecording
                        if not isPlayback and isRecording:
                            # TODO: keep the sequence looping and not play it?
                            # Or restart seq on start play?
                            cursesRingPrint(stdscr,
                                            'Cannot record without playing back')
                            isRecording = False
                        else:
                            cursesRingPrint(
                                stdscr, 'Recording' if isRecording else 'Stopped recording')
                    # Reset
                    elif inputChar == ord('x'):
                        synthOut.reset()
                        synthOut.panic()
                        manualNoteResetCH345(synthOut)
                        cursesRingPrint(stdscr, "Reset output")

                    if isPlayback:
                        # Restart sequence if necessary
                        if sequenceTime >= sequenceTimeLength - timeRoomForError:
                            # TODO: Minimize drift over time
                            if sequenceNumTimesPlayed and sequenceNumTimesPlayed % sequenceNumTimesMeasureDrift == 0:
                                sequenceThisFrameDrift = (currentTime - sequenceDriftStartTime) - (
                                    sequenceTimeLength * sequenceNumTimesMeasureDrift)

                                cursesRingPrint(stdscr, 'Sequence played ' + str(sequenceNumTimesPlayed)
                                                + ' times; drifted ' +
                                                str((currentTime - sequenceFirstStartTime)
                                                    - (sequenceTimeLength * sequenceNumTimesPlayed)) + ', drifted '
                                                + (str(sequenceThisFrameDrift) if math.fabs(
                                                    sequenceThisFrameDrift) > frameRate else ' -negligible- ')
                                                + ' this ' + str(sequenceNumTimesMeasureDrift) + ' drift frame')
                                cursesRingPrint(stdscr, '    (Started at ' + str(sequenceFirstStartTime) + ', last sequence start time ' + str(sequenceLastStartTime) + ', expected last start time ' + str(
                                    sequenceFirstStartTime + (sequenceNumTimesPlayed * sequenceTimeLength)) + ', diff ' + str((sequenceFirstStartTime + (sequenceNumTimesPlayed * sequenceTimeLength)) - sequenceLastStartTime) + ')')
                                sequenceDriftStartTime = currentTime

                            sequenceLastStartTime = currentTime
                            sequenceLastNotePlayedTime = 0.0
                            sequenceNumTimesPlayed += 1

                        # Play sequencer notes if it's time
                        # TODO: sort notes by time? Also, out messages work
                        # strangely
                        for note in sequence:
                            # TODO: this comparison should have a margin of error equal
                            # to the frame rate
                            if note[1] <= sequenceTime and note[1] >= sequenceLastNotePlayedTime:
                                synthOut.send(note[0])
                                sequenceLastNotePlayedTime = max(
                                    sequenceLastNotePlayedTime, note[1])

                                if not sequenceFirstStartTime:
                                    sequenceFirstStartTime = currentTime

                    timeAccumulated -= frameRate
                    timeAccumulated = max(0.0, timeAccumulated)

                if shouldQuit:
                    break

                sleepTime = frameRate - timeAccumulated - timeRoomForError
                if sleepTime > 0:
                    if sequenceNumTimesPlayed:
                        # Make sure we wake up and start the sequence at the right
                        # time
                        sequenceNextStartTime = sequenceLastStartTime + sequenceTimeLength
                        if sleepTime + currentTime > sequenceNextStartTime:
                            cursesRingPrint(stdscr, 'Instead of sleeping for ' + str(sleepTime) + ', sleep for ' +
                                            str(sequenceNextStartTime - currentTime - timeRoomForError) + ' (sequence starts soon)')
                            sleepTime = max(
                                0.0, sequenceNextStartTime - currentTime - timeRoomForError)

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
            manualNoteResetCH345(synthOut)

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
