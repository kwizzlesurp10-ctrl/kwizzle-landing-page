(function () {
  "use strict";
  try {
    var params = new URLSearchParams(window.location.search);
    var twclid = params.get("twclid");
    if (!twclid) {
      return;
    }
    sessionStorage.setItem("kwizzle_twclid", twclid);
    document.cookie =
      "kwizzle_twclid=" +
      encodeURIComponent(twclid) +
      "; path=/; max-age=2592000; SameSite=Lax";
  } catch (_err) {
    /* ignore storage / cookie failures */
  }
})();
