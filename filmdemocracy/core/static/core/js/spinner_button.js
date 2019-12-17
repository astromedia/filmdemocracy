$(document).ready(function() {
    $("#btnSpinner").click(function() {
      // disable button
      $(this).prop("disabled", true);
      // add spinner to button
      $(this).html(
        `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>`
      );
      $("#formSubmit").submit();
    });
    $("#btnSpinnerBanner1").click(function() {
      // disable button
      $(this).prop("disabled", true);
      // add spinner to button
      $(this).html(
        `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>`
      );
      $("#formSubmitBanner1").submit();
    });
    $("#btnSpinnerBanner2").click(function() {
      // disable button
      $(this).prop("disabled", true);
      // add spinner to button
      $(this).html(
        `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>`
      );
      $("#formSubmitBanner2").submit();
    });
    $("#btnSpinnerBanner3").click(function() {
      // disable button
      $(this).prop("disabled", true);
      // add spinner to button
      $(this).html(
        `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>`
      );
      $("#formSubmitBanner3").submit();
    });
});