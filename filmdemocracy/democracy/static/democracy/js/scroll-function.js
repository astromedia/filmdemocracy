window.onscroll = function() {scrollFunction()};

function scrollFunction() {
  if (document.getElementById("club-banner-navigation")) {
    if (document.body.scrollTop > 30 || document.documentElement.scrollTop > 30) {
      document.getElementById("club-banner-navigation").style.boxShadow = "0 0px 15px rgba(0, 0, 0, 0.75)";
      document.getElementById("club-banner-navigation").style.backgroundColor = "#07080a";
      document.getElementById("NavBar").style.boxShadow = "none";
    } else {
      document.getElementById("club-banner-navigation").style.boxShadow = "none";
      document.getElementById("club-banner-navigation").style.backgroundColor = "#121317";
      document.getElementById("NavBar").style.boxShadow = "0 2px 6px rgba(0, 0, 0, 0.85)";
    };
  };
  if (document.getElementById("btn-back-to-top")) {
    if ((window.innerHeight + window.pageYOffset) >= document.body.offsetHeight - 200) {
      document.getElementById("btn-back-to-top").style.display = "block";
    } else {
      document.getElementById("btn-back-to-top").style.display = "none";
    };
  };
}
function topFunction() {
  document.body.scrollTop = 0; // For Safari
  document.documentElement.scrollTop = 0; // For Chrome, Firefox, IE and Opera
}