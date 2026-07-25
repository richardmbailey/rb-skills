(function initialiseConverterInterface() {
  "use strict";

  const converter = window.SafeOperationConverter;
  const form = document.querySelector("#converter-form");
  const sourceValue = document.querySelector("#source-value");
  const sourceUnit = document.querySelector("#source-unit");
  const targetUnit = document.querySelector("#target-unit");
  const swapButton = document.querySelector("#swap-units");
  const result = document.querySelector("#conversion-result");

  if (!converter || !form || !sourceValue || !sourceUnit || !targetUnit || !swapButton || !result) {
    return;
  }

  function showMessage(message, state) {
    result.textContent = message;
    result.dataset.state = state;
  }

  form.addEventListener("submit", function handleConversion(event) {
    event.preventDefault();

    const rawValue = sourceValue.value.trim();
    if (rawValue === "") {
      showMessage("Enter a temperature to convert.", "error");
      return;
    }

    const numericValue = Number(rawValue);
    try {
      const convertedValue = converter.convertTemperature(
        numericValue,
        sourceUnit.value,
        targetUnit.value,
      );
      const sourceLabel = converter.unitLabels[sourceUnit.value];
      const targetLabel = converter.unitLabels[targetUnit.value];
      showMessage(
        `${converter.formatTemperature(numericValue)} ${sourceLabel} = ${converter.formatTemperature(convertedValue)} ${targetLabel}`,
        "success",
      );
    } catch (error) {
      const message = error instanceof Error ? error.message : "The temperature could not be converted.";
      showMessage(message, "error");
    }
  });

  swapButton.addEventListener("click", function swapUnits() {
    const previousSource = sourceUnit.value;
    sourceUnit.value = targetUnit.value;
    targetUnit.value = previousSource;
    showMessage("Units swapped. Convert the current value when ready.", "idle");
  });
})();
