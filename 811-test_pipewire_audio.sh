#!/bin/bash

# Variables for PipeWire components
PIPEWIRE_BIN="pipewire"
WIREPLUMBER_BIN="wireplumber"
PW_AUDIO_BIN="pipewire-pulse"
PW_JACK_BIN="pw-jack"
TEST_AUDIO_FILE="/usr/share/sounds/alsa/Front_Center.wav"
TEMP_RECORD_FILE="/tmp/test_audio_record.wav"

# Function to start a process
start_process() {
  local name="$1"
  local command="$2"
  pgrep -x "$name" > /dev/null
  if [ $? -ne 0 ]; then
    echo "Starting $name..."
    $command &
    sleep 1
    if pgrep -x "$name" > /dev/null; then
      echo "$name started successfully."
    else
      echo "Failed to start $name."
    fi
  else
    echo "$name is already running."
  fi
}

# Start PipeWire components
start_process "pipewire" "$PIPEWIRE_BIN"
start_process "pipewire-pulse" "$PW_AUDIO_BIN"
start_process "wireplumber" "$WIREPLUMBER_BIN"

# Check PipeWire status
echo "Checking PipeWire status..."
if ! pw-cli info; then
  echo "Failed to communicate with PipeWire. Exiting."
  exit 1
fi

# List available audio devices
echo "Listing available audio devices..."
pw-cli ls Node | grep -i 'audio'

# Test audio playback
if command -v aplay > /dev/null; then
  if [ -f "$TEST_AUDIO_FILE" ]; then
    echo "Testing audio playback with aplay..."
    aplay "$TEST_AUDIO_FILE"
    if [ $? -eq 0 ]; then
      echo "Audio playback test successful."
    else
      echo "Audio playback test failed."
    fi
  else
    echo "Test audio file not found: $TEST_AUDIO_FILE"
  fi
else
  echo "'aplay' command not found. Skipping playback test."
fi

# Test audio recording
if command -v arecord > /dev/null; then
  echo "Testing audio recording with arecord..."
  arecord -f cd -d 5 "$TEMP_RECORD_FILE"
  if [ $? -eq 0 ]; then
    echo "Audio recording test successful. Playing back the recorded audio..."
    aplay "$TEMP_RECORD_FILE"
    if [ $? -eq 0 ]; then
      echo "Recorded audio playback successful."
    else
      echo "Recorded audio playback failed."
    fi
    rm -f "$TEMP_RECORD_FILE"
  else
    echo "Audio recording test failed."
  fi
else
  echo "'arecord' command not found. Skipping recording test."
fi

# Test JACK compatibility (if pw-jack is installed)
if command -v $PW_JACK > /dev/null; then
  echo "Testing JACK compatibility using pw-jack..."
  $PW_JACK -l || echo "Failed to list JACK clients."
else
  echo "Skipping JACK test. pw-jack not found."
fi

echo "PipeWire audio testing complete."
