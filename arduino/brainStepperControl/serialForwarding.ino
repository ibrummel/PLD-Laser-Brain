void forwardSerial1() {
    Serial1.print(inCommandSerForward);
    commandReady = false;
    clearAxisModVars();
}

void readSerial1() {
    // Basic implementation. line end characters etc need configuration if this is connected.
    if (Serial1.available() > 0) {
        Serial.println(Serial1.read());
    }
    commandReady = false;
    clearAxisModVars();
}