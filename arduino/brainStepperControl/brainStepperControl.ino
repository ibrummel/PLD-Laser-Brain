#include <AccelStepper_50pctDuty.h>
#include <AccelStepper.h>

enum USER_PINS {
  SUB_RUN = 18,
  SUB_STEP = 2,
  SUB_DIR = 3,
  TARGET_RUN = 19,
  TARGET_STEP = 4,
  TARGET_DIR = 5,
  LASER_RUN = 20,
  LASER_STEP = 11,
  LASER_DIR = A0 // A0 is used as it is currently not connected to anything and we don't need a direction pin here.
};

enum USER_CONST {
  SUB_STEPS_PER_REV = 1000,
  CAROUSEL_STEPS_PER_REV = 6000
};

// Define the available stepper motors
AccelStepper50pctDuty substrate(AccelStepper50pctDuty::DRIVER, SUB_STEP, SUB_DIR);
AccelStepper50pctDuty target(AccelStepper50pctDuty::DRIVER, TARGET_STEP, TARGET_DIR);

// Define the laser pulsing, using a stepper motor that just runs at constant speed
AccelStepper laser(AccelStepper::DRIVER, LASER_STEP, LASER_DIR);

//Define variables for serial input handling
const byte numChars = 32;
char inCommandChars[numChars];
char tempChars[numChars];        // temporary array for use when parsing

// variables to hold the parsed data
char inCommandAxis = 'z';
char inCommandType = 'z';
char inCommandPinNum = 0;

char inCommandSerForward[numChars];
char inCommandParam = 'z';
long inCommandValLong;
float inCommandValFloat;

boolean newData = false;

// Define other variables
bool commandReady = false;    // Flag to signal command from serial is ready for procesesing
bool laserRunIndef = false;   // Flag for running laser indefinitely
bool subRunIndef = false;     // Flag for running motors indefinitely: substrate
bool targetRunIndef = false;  // Flag for running motors indefinitely: target
int subDirIndef = 0;          // Flag for indefinite movement direction: substrate
int targetDirIndef = 0;       // Flag for indefinite movement direction: target
int currentTarget = 0;        // Stores the target ID for the closest target position to the current position
int rasterSteps = 0;          // Stores the number of steps across the target, set based on target size.
bool rasterOn = false;        // Sets the raster on off state
bool centering = false;       // Set based on whether the target is returning to center
int rasterSide = 1;           // Which side of the target should be moved to

/********************************************** Main run loops **********************************************/
void setup() {
  Serial.begin(115200);
  //Serial1.begin(9600);         // Baud rate will need to be adjusted to match the device that is connected in future

  // ** Set up motor limits and parameters ** //
  substrate.setMaxSpeed(1000);  // set the max substrate speed to 4rps
  target.setMaxSpeed(1000); // set max target speed as 1 rps FIXME: This might be too fast

  substrate.setAcceleration(20000); // Probably going to stick with runSpeed for constant speeds since we have plenty of torque
  target.setAcceleration(1000); // set acceleration limits

  // Invert pins for the directions to match reality
  substrate.setPinsInverted(true, false, true);
  // target.setPinsInverted(directionInvert=true, stepInvert=false);

  // ** Set up laser limits and parameters ** //
  laser.setMaxSpeed(20);       // Don't want laser to run above 20 Hz
  laser.setAcceleration(500000);
  laser.setMinPulseWidth(20);  // Laser requires a >=15 micrsecond pulse
  laser.setSpeed(5);

  // Set up pins as in or output
  setupPins();
}

void loop() {
  recCommand();                           // Check if there is a command to receive from the serial input
  if (newData == true) {
    parseData();                        // if there is new data parse it
    newData = false;                    // Clears the new data variable
    commandReady = true;                // Flags for setting pins or updating motor params
    //easyShowParsedData();
  }
  if (commandReady == true) {

    switch (inCommandAxis) {
      case 'o':
        digitalPinWrite();
        break;
      case 'i':
        Serial.println(digitalPinRead());
        break;
      case 'f':
        forwardSerial1();
        break;
      case 'r':
        readSerial1();
        break;
      case 's':
        updateMotorParams(substrate, 's');
        break;
      case 't':
        updateMotorParams(target, 't');
        break;
      case 'l':
        updateLaserParams(laser);
        break;
      default:
        commandReady = false; // Protects against erroneous commands sending the arduino into a loop
        break;
    }
  }

  // Handle rastering
  // If rastering is complete/stopped (rasterSteps == 0) and we are
  // not already in the process of recentering, move back to center
  if (rasterSteps == 0 && centering == false && rasterOn == true) {
    target.moveTo(currentTarget * (CAROUSEL_STEPS_PER_REV / 6));
    centering = true;
  }
  // If rastering is complete/stopped (rasterSteps == 0) and the centering
  // flag is set, check if the move is complete.
  else if (rasterSide == 0 && centering == true && rasterOn == true) {
    // if the move is complete, set the centering flag as false
    if (target.distanceToGo() == 0) {
      centering = false;
      rasterOn = false;
    }
  }
  // If raster is activated and the last move is complete, move the other way
  else if (rasterOn == true && target.distanceToGo() == 0) {
    rasterSide *= -1;   // Switch which direction to move
    target.moveTo((currentTarget * (CAROUSEL_STEPS_PER_REV / 6)) + (rasterSteps * rasterSide)); // Set the new goal position
  }

  // Handle running without a target position
  if (subRunIndef == true) substrate.move(100 * subDirIndef);
  if (targetRunIndef == true) target.move(100 * targetDirIndef);
  if (laserRunIndef == true) laser.move(100);

  // Set cross-board GPIO pins as needed

  if (target.isRunning()) digitalWrite(TARGET_RUN, HIGH);
  else if (!target.isRunning() && (target.currentPosition() >= 6000 || target.currentPosition() < 0)) {
    // Keep the target position a positive number by adding multiples of the rotation
    while (target.currentPosition() < 0) target.setCurrentPosition(target.currentPosition() + CAROUSEL_STEPS_PER_REV);
    // Keep the target position between 0 and 6000
    target.setCurrentPosition(target.currentPosition() % CAROUSEL_STEPS_PER_REV);
  }
  else digitalWrite(TARGET_RUN, HIGH);

  if (substrate.isRunning()) digitalWrite(SUB_RUN, HIGH);
  else digitalWrite(SUB_RUN, LOW);

  if (laser.isRunning()) digitalWrite(LASER_RUN, HIGH);
  else digitalWrite(LASER_RUN, LOW);

  // Handle running the motors to their positions
  target.run();
  substrate.run();
  laser.run();

  // Set the current target position
  currentTarget = round((fmod(target.currentPosition(), CAROUSEL_STEPS_PER_REV) / CAROUSEL_STEPS_PER_REV) * 6);
}
