(function () {
  "use strict";

  const panel = document.getElementById("filter-panel");
  const backdrop = document.getElementById("filter-backdrop");
  const toggleBtn = document.getElementById("filter-toggle");
  const filterSearch = document.getElementById("filter-search");
  const lozengeBar = document.getElementById("filter-lozenges");
  const resultCount = document.getElementById("filter-result-count");
  const clearAllBtn = document.getElementById("filter-clear-all");
  const includeRef = document.getElementById("include-reference");
  const tbody = document.getElementById("recipe-tbody");

  if (!tbody || !panel) return;

  const rows = Array.from(tbody.querySelectorAll("tr[data-facets]"));
  const totalBrowsable = rows.filter(
    (r) => r.dataset.reference !== "true"
  ).length;

  /** @type {Map<string, Set<string>>} */
  const selected = new Map();

  function parseSelected() {
    selected.clear();
    document.querySelectorAll(".filter-value:checked").forEach((el) => {
      const facet = el.dataset.facet;
      const value = el.dataset.value;
      if (!selected.has(facet)) selected.set(facet, new Set());
      selected.get(facet).add(value);
    });
  }

  function selectedCount() {
    let n = 0;
    selected.forEach((s) => (n += s.size));
    return n;
  }

  function rowMatches(row) {
    const tokens = (row.dataset.facets || "").split(/\s+/).filter(Boolean);
    for (const [facet, values] of selected) {
      if (!values.size) continue;
      const ok = [...values].some((v) => tokens.includes(`${facet}:${v}`));
      if (!ok) return false;
    }
    return true;
  }

  function updateVisibility() {
    const showRef = includeRef && includeRef.checked;
    let visible = 0;
    rows.forEach((row) => {
      const isRef = row.dataset.reference === "true";
      if (isRef && !showRef) {
        row.hidden = true;
        return;
      }
      const match = rowMatches(row);
      row.hidden = !match;
      if (match && (!isRef || showRef)) visible += 1;
    });
    const base = showRef ? rows.length : totalBrowsable;
    if (resultCount) {
      resultCount.textContent = `Showing ${visible} of ${base} recipes`;
    }
  }

  function renderLozenges() {
    if (!lozengeBar) return;
    lozengeBar.innerHTML = "";
    const hasSelection = selectedCount() > 0;
    if (clearAllBtn) clearAllBtn.hidden = !hasSelection;

    for (const [facet, values] of selected) {
      const groupLabel =
        document.querySelector(`[data-facet-group="${facet}"]`)?.dataset
          .groupLabel || facet;
      values.forEach((value) => {
        const pill = document.createElement("button");
        pill.type = "button";
        pill.className = "filter-lozenge";
        pill.dataset.facet = facet;
        pill.dataset.value = value;
        const label =
          document.querySelector(
            `.filter-value[data-facet="${facet}"][data-value="${value}"]`
          )?.dataset.label || value;
        pill.innerHTML = `${groupLabel}: ${label} <span aria-hidden="true">×</span>`;
        pill.addEventListener("click", () => {
          const cb = document.querySelector(
            `.filter-value[data-facet="${facet}"][data-value="${value}"]`
          );
          if (cb) cb.checked = false;
          applyFilters();
        });
        lozengeBar.appendChild(pill);
      });
    }
  }

  function updateToggleLabel() {
    if (!toggleBtn) return;
    const n = selectedCount();
    toggleBtn.textContent = n ? `Filters (${n})` : "Filters";
  }

  function applyFilters() {
    parseSelected();
    renderLozenges();
    updateToggleLabel();
    updateVisibility();
  }

  function openPanel() {
    panel.hidden = false;
    if (backdrop) backdrop.hidden = false;
    panel.setAttribute("aria-hidden", "false");
    if (filterSearch) {
      filterSearch.value = "";
      filterSearch.dispatchEvent(new Event("input"));
      filterSearch.focus();
    }
  }

  function closePanel() {
    panel.hidden = true;
    if (backdrop) backdrop.hidden = true;
    panel.setAttribute("aria-hidden", "true");
  }

  function clearAll() {
    document.querySelectorAll(".filter-value:checked").forEach((el) => {
      el.checked = false;
    });
    applyFilters();
  }

  function clearFacet(facet) {
    document
      .querySelectorAll(`.filter-value[data-facet="${facet}"]:checked`)
      .forEach((el) => {
        el.checked = false;
      });
    applyFilters();
  }

  document.querySelectorAll(".filter-group-toggle").forEach((btn) => {
    btn.addEventListener("click", () => {
      const group = btn.closest(".filter-group");
      if (!group) return;
      const expanded = btn.getAttribute("aria-expanded") === "true";
      btn.setAttribute("aria-expanded", expanded ? "false" : "true");
      const list = group.querySelector(".filter-values");
      if (list) list.hidden = expanded;
    });
  });

  document.querySelectorAll(".filter-clear-facet").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      clearFacet(btn.dataset.facet);
    });
  });

  document.querySelectorAll(".filter-value").forEach((cb) => {
    cb.addEventListener("change", applyFilters);
  });

  if (toggleBtn) {
    toggleBtn.addEventListener("click", () => {
      if (panel.hidden) openPanel();
      else closePanel();
    });
  }

  document.getElementById("filter-close")?.addEventListener("click", closePanel);
  backdrop?.addEventListener("click", closePanel);

  if (filterSearch) {
    filterSearch.addEventListener("input", () => {
      const q = filterSearch.value.trim().toLowerCase();
      document.querySelectorAll(".filter-value-label").forEach((label) => {
        const text = label.textContent.toLowerCase();
        const row = label.closest(".filter-value-row");
        if (row) row.hidden = q && !text.includes(q);
      });
      document.querySelectorAll(".filter-group").forEach((group) => {
        const visible = group.querySelectorAll(
          ".filter-value-row:not([hidden])"
        ).length;
        group.hidden = q && visible === 0;
      });
    });
  }

  clearAllBtn?.addEventListener("click", clearAll);
  includeRef?.addEventListener("change", updateVisibility);

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !panel.hidden) closePanel();
  });

  applyFilters();
})();
