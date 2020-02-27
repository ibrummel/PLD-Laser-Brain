void updateMotorParams(AccelStepper50pctDuty & motor, char axis) {           // Passes motor by reference so that it can be used for sub and targets

  if (inCommandType == 'u') {
    switch (inCommandParam) {
      case 'a':                       // Set acceleration if parameter to update is 'a'
        motor.setAcceleration(inCommandValFloat);
        commandReady = false;
        break;
      case 'm':                       // Set max speed if parameter to update is 'm'
        motor.setMaxSpeed(inCommandValFloat);
        commandReady = false;
        break;
      case 'v':                       // Set motor speed if parameter to update is 'v'elocity
        motor.setSpeed(inCommandValFloat);
        commandReady = false;
        break;
      case 'g':                       // Set new goal position (targets are set by target number 0 indexed)
        if (axis == 's') {          // Stop running indefinitely if we now have a goal to get to.
          subRunIndef = false;
          subDirIndef = 0;
          motor.moveTo(inCommandValLong);
        }
        else if (axis == 't') {
          targetRunIndef = false;
          targetDirIndef = 0;
          motor.move(shortestMoveToTarget(inCommandValLong * 1000));
          // Move to wherever, final position limiting is handled in main loop
        }
        commandReady = false;
        break;
      case 't':
        motor.move(inCommandValLong);
        commandReady = false;
        break;
      case 'p':
        motor.setCurrentPosition(inCommandValLong);
        commandReady = false;
        break;
      case 'd':                       // Used for manual stepping
        if (inCommandValLong == 1) { // Move cw without a goal
          if (axis == 's') {
            subRunIndef = true;
            subDirIndef = 1;
          }
          else if (axis == 't') {
            targetRunIndef = true;
            targetDirIndef = 1;
          }
        }
        else if (inCommandValLong == -1) {    // Move ccw without a goal
          if (axis == 's') {
            subRunIndef = true;
            subDirIndef = -1;
          }
          else if (axis == 't') {
            targetRunIndef = true;
            targetDirIndef = -1;
          }
        }
        break;
      case 'r':
        if (inCommandAxis != 't') {
          commandReady = false;     // Only raster if the target is the selected command axis
          break;                    // Break early
        }

        // If we are currently centering the target, maintain the center value,
        // otherwise set raster center to the current position
        if (centering == false) {
          rasterCenter = motor.targetPosition();
        }

        // Set the raster steps based on input
        if (inCommandValLong == 0) {
          rasterSteps = 0;
          rasterSide = 0;   // Flag main loop to move back to target center
          rasterOn = false;
        }
        else if (inCommandValLong == 1) {
          rasterSteps = 31;
          rasterOn = true;
        }
        else if (inCommandValLong == 2) {
          rasterSteps = 63;
          rasterOn = true;
        }
        commandReady = false;
        break;
    }
  }
  else if (inCommandType == 'q') {
    switch (inCommandParam) {
      case 'p':
        Serial.println(motor.currentPosition());
        break;
      case 'm':
        Serial.println(motor.maxSpeed());
        break;
      case 'v':
        Serial.println(motor.speed());
        break;
      case 'g':
        Serial.println(motor.targetPosition());
        break;
      case 'd':
        Serial.println(motor.distanceToGo());
        break;
      case 'r':
        Serial.println(motor.isRunning());
        break;
    }
    commandReady = false;
  }
  else if (inCommandType == 'h') {
    // May need to consider cranking acceleration here to stop faster
    motor.stop();                   // May need to switch to disableOutputs to up reaction speed
    if (axis == 's') {
      subRunIndef = false;
      subDirIndef = 0;
    }
    else if (axis == 't') {
      targetRunIndef = false;
      targetDirIndef = 0;
    }
    commandReady = false;              // Finishes this command and prevents re updating
  }
  if (commandReady == false) {                  // If we set command ready to false, clear command variable values
    clearAxisModVars();
  }
}

int shortestMoveToTarget(int finalPos) {
  // Function adapted from https://stackoverflow.com/questions/9505862/shortest-distance-between-two-degree-marks-on-a-circle
  // Origin position is from the target motor's current position
  int origin = target.currentPosition();
  // Declare variable to hold path to return
  int path = 0;
  // The magnitude of the path difference, modulo the rotation (accounts for being way off)
  int deltaMod = fmod(abs(origin - finalPos), TARGET_STEPS_PER_REV);

  //There is a shorter path in opposite direction if the travel is more than half the rotation
  if (deltaMod > (TARGET_STEPS_PER_REV / 2) ) {
    // Path is set to a total revolution - the magnitude of the path difference (because the magnitude of
    //  the path difference is larger than half of a rotation)
    path = (TARGET_STEPS_PER_REV - deltaMod);
    // Set the sign for path based on the relationship between the target and the origin. Counterclockwise
    //  if the finalPos > origin because we are going to go backward
    if (finalPos > origin) path *= -1;
  }
  // Otherwise there is not a shorter path 
  else {
    // Set the path length to the magnitude of the path difference
    path = deltaMod;
    // Set the sign of the path based on the relationship between target and origin. Condition has
    //  switched from above because we haven't flipped the path length
    if (origin > finalPos) path *= -1;
  }

  return path;

}
