(function($) {
  $.fn.currencyInput = function() {
    this.each(function() {
      var wrapper = $("<div class='currency-input' />");
      $(this).wrap(wrapper);
      $(this).before("<span class='currency-symbol'>&dollar;</span>");
      $(this).change(function() {
        var min = parseFloat($(this).attr("min"));
        var max = parseFloat($(this).attr("max"));
        var value = this.valueAsNumber;
        if(value < min)
          value = min;
        else if(value > max)
          value = max;
        $(this).val(value.toFixed(2));
      });
    });
  };
})(jQuery);

function csrfToken() {
  var input = document.querySelector('input[name="_csrf_token"]');
  return input ? input.value : "";
}

function bindPlaceCreateForm(modal, modalBody) {
  var form = document.getElementById("place-create-form");
  if (!form) {
    return;
  }

  form.addEventListener("submit", function(e) {
    e.preventDefault();
    var data = new FormData(form);

    fetch(form.action, {
      method: "POST",
      headers: {
        "Accept": "application/json",
        "X-CSRF-Token": csrfToken(),
      },
      body: data,
    })
      .then(function(response) {
        return response.json().then(function(body) {
          return { ok: response.ok, body: body };
        });
      })
      .then(function(result) {
        if (result.ok && result.body.ok) {
          var select = document.getElementById("place_id");
          var option = document.createElement("option");
          option.value = result.body.id;
          option.textContent = result.body.label;
          option.selected = true;
          select.appendChild(option);
          modal.hide();
          return;
        }
        if (result.body.html) {
          modalBody.innerHTML = result.body.html;
          bindPlaceCreateForm(modal, modalBody);
        }
      });
  });
}

function currentTheme() {
  return document.documentElement.dataset.theme === "light" ? "light" : "dark";
}

function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  var sun = document.querySelector(".theme-icon-sun");
  var moon = document.querySelector(".theme-icon-moon");
  if (sun) {
    sun.hidden = theme !== "dark";
  }
  if (moon) {
    moon.hidden = theme !== "light";
  }
}

function bindThemeToggle() {
  var toggle = document.getElementById("theme-toggle");
  if (!toggle) {
    return;
  }

  toggle.addEventListener("click", function() {
    var next = currentTheme() === "dark" ? "light" : "dark";
    applyTheme(next);

    var url = toggle.getAttribute("data-preferences-url");
    if (!url) {
      return;
    }

    var data = new FormData();
    data.append("theme", next);
    fetch(url, {
      method: "POST",
      headers: {
        "Accept": "application/json",
        "X-CSRF-Token": csrfToken(),
      },
      body: data,
    });
  });
}

$(document).ready(function() {
  $("input.currency").currencyInput();
  bindThemeToggle();

  var addPlaceLink = document.getElementById("add-place-link");
  var modalEl = document.getElementById("placeCreateModal");
  if (!addPlaceLink || !modalEl) {
    return;
  }

  var modal = new bootstrap.Modal(modalEl);
  var modalBody = document.getElementById("place-create-modal-body");

  addPlaceLink.addEventListener("click", function(e) {
    e.preventDefault();
    modalBody.innerHTML = '<p class="text-muted mb-0">Loading…</p>';
    modal.show();

    fetch(addPlaceLink.href)
      .then(function(response) { return response.text(); })
      .then(function(html) {
        modalBody.innerHTML = html;
        bindPlaceCreateForm(modal, modalBody);
      });
  });
});
