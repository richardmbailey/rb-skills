(function initialiseSafeOperationConverter(global) {
  "use strict";

  const ABSOLUTE_ZERO = Object.freeze({
    C: -273.15,
    F: -459.67,
    K: 0,
  });

  const UNIT_LABELS = Object.freeze({
    C: "°C",
    F: "°F",
    K: "K",
  });

  function requireUnit(unit) {
    if (!Object.prototype.hasOwnProperty.call(ABSOLUTE_ZERO, unit)) {
      throw new RangeError(`Unknown temperature unit: ${String(unit)}`);
    }
  }

  function requireFiniteTemperature(value, unit) {
    if (typeof value !== "number" || !Number.isFinite(value)) {
      throw new TypeError("Temperature must be a finite number.");
    }

    if (value < ABSOLUTE_ZERO[unit]) {
      throw new RangeError(
        `Temperature cannot be below absolute zero (${ABSOLUTE_ZERO[unit]} ${UNIT_LABELS[unit]}).`,
      );
    }
  }

  function toKelvin(value, fromUnit) {
    if (fromUnit === "K") {
      return value;
    }
    if (fromUnit === "F") {
      return (value + 459.67) * (5 / 9);
    }
    return value + 273.15;
  }

  function fromKelvin(value, toUnit) {
    if (toUnit === "K") {
      return value;
    }
    if (toUnit === "F") {
      return value * (9 / 5) - 459.67;
    }
    return value - 273.15;
  }

  function convertTemperature(value, fromUnit, toUnit) {
    requireUnit(fromUnit);
    requireUnit(toUnit);
    requireFiniteTemperature(value, fromUnit);

    if (fromUnit === toUnit) {
      return value;
    }

    return fromKelvin(toKelvin(value, fromUnit), toUnit);
  }

  function formatTemperature(value) {
    if (typeof value !== "number" || !Number.isFinite(value)) {
      throw new TypeError("A finite converted value is required for formatting.");
    }

    const displayValue = Math.abs(value) < 0.005 ? 0 : value;
    return displayValue.toFixed(2);
  }

  global.SafeOperationConverter = Object.freeze({
    absoluteZero: ABSOLUTE_ZERO,
    convertTemperature,
    formatTemperature,
    unitLabels: UNIT_LABELS,
  });
})(window);
