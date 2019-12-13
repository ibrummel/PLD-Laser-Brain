void digitalPinWrite() {
    if (inCommandParam == 'w') {              // If told to write set pin high
        digitalWrite(inCommandPinNum, HIGH);
    }
    else if (inCommandParam == 'c') {         // if told to clear set pin low
        digitalWrite(inCommandPinNum, LOW);
    }
    commandReady = false;                   // Set command ready false so that we can return to normal operation
    clearAxisModVars();                     // Clear variables from serial read now that we are done with them
}

int digitalPinRead() {
    int status;                             // Create a variable to hold the pin status
    status = digitalRead(inCommandPinNum);  // Read the pin status to the variable status
    clearAxisModVars();                     // Clear variables from serial read now that we are done with them
    
    commandReady = false;                   // Set command ready false so that we can return to normal operation
    return status;
}

void setupPins() {
    // Configure pins as Input/Output
    // NOT USED YET
    // pinMode(12, OUTPUT)
    // pinMode(13, INPUT)
    pinMode(2, OUTPUT);   // GPIO_HV: 1
    pinMode(3, OUTPUT);   // GPIO_HV: 2
    pinMode(4, OUTPUT);   // GPIO_HV: 3
    pinMode(5, OUTPUT);   // GPIO_HV: 4
    pinMode(6, OUTPUT);   // GPIO_HV: 6
    pinMode(7, OUTPUT);   // GPIO_HV: 7
    pinMode(8, OUTPUT);   // GPIO_HV: 8
    pinMode(9, OUTPUT);   // GPIO_HV: 9
    pinMode(10, OUTPUT);  // BNC_HV: 1
    pinMode(11, OUTPUT);  // BNC_HV: 2 
    pinMode(12, OUTPUT);  // BNC_HV: 3 
    pinMode(13, OUTPUT);  // Builtin LED
    /* 
    Analogue pin A0 is: 14
    Analogue pin A1 is: 15
    Analogue pin A2 is: 16
    Analogue pin A3 is: 17
    Analogue pin A4 is: 18
    Analogue pin A5 is: 19
    Analogue pin A6 is: 20
    Analogue pin A7 is: 21
    */
    pinMode(16, OUTPUT);  // BNC_HV: 4  
    pinMode(17, OUTPUT);  // BNC_HV: 5
    pinMode(18, OUTPUT);  // PiGPIO: 21
    pinMode(19, OUTPUT);  // PiGPIO: 20
    pinMode(20, OUTPUT);  // PiGPIO: 19
    pinMode(21, OUTPUT);  // PiGPIO: 16
}