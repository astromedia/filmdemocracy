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
});