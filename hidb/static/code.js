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

function bindEmbedCreateForm(formId, selectId, modal, modalBody) {
  var form = document.getElementById(formId);
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
          var select = document.getElementById(selectId);
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
          bindEmbedCreateForm(formId, selectId, modal, modalBody);
        }
      });
  });
}

var THEME_CYCLE = ["light", "dark", "system"];

function resolveEffectiveTheme(preference) {
  if (preference === "light" || preference === "dark") {
    return preference;
  }
  if (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) {
    return "dark";
  }
  return "light";
}

function nextThemePreference(current) {
  var idx = THEME_CYCLE.indexOf(current);
  if (idx === -1) {
    return "light";
  }
  return THEME_CYCLE[(idx + 1) % THEME_CYCLE.length];
}

function updateThemeIcons(preference) {
  var sun = document.querySelector(".theme-icon-sun");
  var moon = document.querySelector(".theme-icon-moon");
  var system = document.querySelector(".theme-icon-system");
  if (sun) {
    sun.hidden = preference !== "light";
  }
  if (moon) {
    moon.hidden = preference !== "dark";
  }
  if (system) {
    system.hidden = preference !== "system";
  }
}

function applyThemePreference(preference) {
  document.documentElement.dataset.theme = resolveEffectiveTheme(preference);
  updateThemeIcons(preference);
  var toggle = document.getElementById("theme-toggle");
  if (toggle) {
    toggle.setAttribute("data-theme-preference", preference);
    toggle.title = "Theme: " + preference + " (click to change)";
    toggle.setAttribute("aria-label", "Change theme (current: " + preference + ")");
  }
}

function bindThemeToggle() {
  var toggle = document.getElementById("theme-toggle");
  if (!toggle) {
    return;
  }

  var preference = toggle.getAttribute("data-theme-preference") || "dark";
  applyThemePreference(preference);

  if (window.matchMedia) {
    window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", function() {
      var current = toggle.getAttribute("data-theme-preference");
      if (current === "system") {
        applyThemePreference("system");
      }
    });
  }

  toggle.addEventListener("click", function() {
    var current = toggle.getAttribute("data-theme-preference") || "dark";
    var next = nextThemePreference(current);
    applyThemePreference(next);

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
    }).then(function() {
      toggle.setAttribute("data-theme-preference", next);
    });
  });
}

function bindEmbedModal(linkId, modalId, bodyId, formId, selectId) {
  var link = document.getElementById(linkId);
  var modalEl = document.getElementById(modalId);
  if (!link || !modalEl) {
    return;
  }

  var modal = new bootstrap.Modal(modalEl);
  var modalBody = document.getElementById(bodyId);

  link.addEventListener("click", function(e) {
    e.preventDefault();
    modalBody.innerHTML = '<p class="text-muted mb-0">Loading…</p>';
    modal.show();

    fetch(link.href)
      .then(function(response) { return response.text(); })
      .then(function(html) {
        modalBody.innerHTML = html;
        bindEmbedCreateForm(formId, selectId, modal, modalBody);
      });
  });
}

function bindPhotoReorder() {
  var grid = document.getElementById("photo-grid");
  if (!grid) {
    return;
  }

  grid.addEventListener("click", function(e) {
    var card = e.target.closest(".col-6, .col-md-4, .col-lg-3");
    if (!card) {
      return;
    }
    if (e.target.classList.contains("photo-move-up")) {
      var prev = card.previousElementSibling;
      if (prev) {
        grid.insertBefore(card, prev);
      }
    }
    if (e.target.classList.contains("photo-move-down")) {
      var next = card.nextElementSibling;
      if (next) {
        grid.insertBefore(next, card);
      }
    }
  });
}

$(document).ready(function() {
  $("input.currency").currencyInput();
  bindThemeToggle();
  bindEmbedModal("add-place-link", "placeCreateModal", "place-create-modal-body", "place-create-form", "place_id");
  bindEmbedModal("add-unit-link", "unitCreateModal", "unit-create-modal-body", "unit-create-form", "unit_id");
  bindPhotoReorder();
});
