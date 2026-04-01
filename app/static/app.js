const uploadForm = document.querySelector("#upload-form");
const searchForm = document.querySelector("#search-form");
const filtersForm = document.querySelector("#filters-form");
const cards = document.querySelector("#cards");
const resultsCount = document.querySelector("#results-count");
const uploadStatus = document.querySelector("#upload-status");
const searchSummary = document.querySelector("#search-summary");
const libraryError = document.querySelector("#library-error");
const classificationDetail = document.querySelector("#classification-detail");
const viewTabs = [...document.querySelectorAll(".view-tab")];
const viewPanels = {
  grid: document.querySelector("#grid-view"),
  classification: document.querySelector("#classification-view"),
};
let searchDebounceTimer = null;
let activeView = "grid";
let currentItems = [];
let selectedGarmentId = null;

// This object is the single source of truth for the active dropdown filters.
const activeFilters = {};

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function buildFilterSelect(key, values) {
  const wrapper = document.createElement("label");
  wrapper.innerHTML = `
    <span>${key.replaceAll("_", " ")}</span>
    <select data-filter-key="${key}">
      <option value="">All</option>
      ${values.map((value) => `<option value="${escapeHtml(value)}">${escapeHtml(value)}</option>`).join("")}
    </select>
  `;
  const select = wrapper.querySelector("select");
  if (activeFilters[key]) {
    select.value = activeFilters[key];
  }
  return wrapper;
}

function renderFilters(filters) {
  filtersForm.innerHTML = "";
  Object.entries(filters).forEach(([key, values]) => {
    if (!values.length) {
      return;
    }
    filtersForm.appendChild(buildFilterSelect(key, values));
  });
}

function annotationMarkup(item) {
  if (!item.annotations.length) {
    return `<p class="muted">No designer annotations yet.</p>`;
  }
  const rows = item.annotations
    .map(
      (annotation) => `
        <li>
          <strong>User Note:</strong> ${escapeHtml(annotation.note)}
          <div class="badge-row">
            ${annotation.tags.map((tag) => `<span class="badge">${escapeHtml(tag)}</span>`).join("")}
          </div>
        </li>
      `,
    )
    .join("");
  return `<ul class="annotation-list">${rows}</ul>`;
}

function detailField(label, value) {
  return `
    <div class="detail-field">
      <label>${escapeHtml(label)}</label>
      <p>${escapeHtml(value || "Not available")}</p>
    </div>
  `;
}

function badgeMarkup(values) {
  if (!values || !values.length) {
    return `<p class="muted">None</p>`;
  }
  return `<div class="badge-row">${values.map((value) => `<span class="badge">${escapeHtml(value)}</span>`).join("")}</div>`;
}

function formatUsd(value) {
  if (value === null || value === undefined) {
    return "Not available";
  }
  return `$${Number(value).toFixed(6)}`;
}

function setActiveView(view) {
  activeView = view;
  viewTabs.forEach((button) => {
    const isActive = button.dataset.view === view;
    button.classList.toggle("is-active", isActive);
    button.setAttribute("aria-selected", String(isActive));
  });
  Object.entries(viewPanels).forEach(([key, panel]) => {
    panel.classList.toggle("is-active", key === view);
  });
}

function selectedItem() {
  return currentItems.find((item) => item.id === selectedGarmentId) || null;
}

function ensureSelectedItem(preferredId = null) {
  const ids = new Set(currentItems.map((item) => item.id));
  if (preferredId && ids.has(preferredId)) {
    selectedGarmentId = preferredId;
    return;
  }
  if (selectedGarmentId && ids.has(selectedGarmentId)) {
    return;
  }
  selectedGarmentId = currentItems.length ? currentItems[0].id : null;
}

function renderCards(items) {
  resultsCount.textContent = `${items.length} looks`;
  if (!items.length) {
    cards.innerHTML = `<div class="empty">No images matched the current search.</div>`;
    return;
  }

  cards.innerHTML = items
    .map(
      (item) => `
        <article class="card ${item.id === selectedGarmentId ? "is-selected" : ""}" data-garment-id="${item.id}">
          <img src="${escapeHtml(item.image_url)}" alt="${escapeHtml(item.description)}" />
          <div class="card-body">
            <p class="muted">${escapeHtml(item.designer || "Unknown designer")} • ${escapeHtml(item.location_context.city || item.location_context.country || "Unknown location")}</p>
            <div class="card-title-row">
              <h3>${escapeHtml(item.garment_type || "Fashion look")}</h3>
              <button type="button" class="card-select" data-garment-id="${item.id}">Open</button>
            </div>
            <p>${escapeHtml(item.description)}</p>

            <p class="muted">AI Metadata</p>
            <div class="badge-row">
              ${item.ai_tags.map((tag) => `<span class="badge">${escapeHtml(tag)}</span>`).join("")}
              ${item.color_palette.map((tag) => `<span class="badge">${escapeHtml(tag)}</span>`).join("")}
            </div>
          </div>
        </article>
      `,
    )
    .join("");
}

function renderLibraryError(message) {
  libraryError.textContent = message || "";
}

function renderClassificationDetail() {
  const item = selectedItem();
  if (!item) {
    classificationDetail.innerHTML = `
      <div class="empty detail-empty">
        Upload or select an image from the grid to see the full model classification.
      </div>
    `;
    return;
  }

  classificationDetail.innerHTML = `
    <div class="detail-layout">
      <section class="detail-image-panel">
        <div class="detail-image-frame">
          <img src="${escapeHtml(item.image_url)}" alt="${escapeHtml(item.description)}" />
        </div>
      </section>
      <section class="detail-info-panel">
        <div class="detail-section">
          <p class="muted">${escapeHtml(item.designer || "Unknown designer")} • ${escapeHtml(item.original_filename)}</p>
          <h3>${escapeHtml(item.garment_type || "Fashion look")}</h3>
          <p class="detail-copy">${escapeHtml(item.description)}</p>
        </div>

        <div class="detail-section">
          <h3>Classification Data</h3>
          <div class="detail-grid">
            ${detailField("Garment Type", item.garment_type)}
            ${detailField("Style", item.style)}
            ${detailField("Material", item.material)}
            ${detailField("Pattern", item.pattern)}
            ${detailField("Season", item.season)}
            ${detailField("Occasion", item.occasion)}
            ${detailField("Consumer Profile", item.consumer_profile)}
            ${detailField("Designer", item.designer)}
            ${detailField("Continent", item.location_context.continent)}
            ${detailField("Country", item.location_context.country)}
            ${detailField("City", item.location_context.city)}
            ${detailField("Captured At", item.captured_at)}
          </div>
        </div>

        <div class="detail-section">
          <h3>AI Tags</h3>
          ${badgeMarkup(item.ai_tags)}
          <h3>Colors</h3>
          ${badgeMarkup(item.color_palette)}
          <h3>Trend Notes</h3>
          ${badgeMarkup(item.trend_notes)}
        </div>

        <div class="detail-section">
          <h3>Designer Annotations</h3>
          ${annotationMarkup(item)}
          <form class="annotation-form" data-garment-id="${item.id}">
            <label>
              Note
              <textarea name="note" rows="2" placeholder="Add a designer note"></textarea>
            </label>
            <label>
              Tags
              <input type="text" name="tags" placeholder="neckline, artisan market" />
            </label>
            <button type="submit">Save Annotation</button>
          </form>
        </div>

        <div class="detail-section">
          <h3>Usage And Cost</h3>
          <div class="detail-grid">
            ${detailField("Usage Source", item.token_usage.source)}
            ${detailField("Model", item.token_usage.model_name)}
            ${detailField("Input Tokens", item.token_usage.input_tokens)}
            ${detailField("Output Tokens", item.token_usage.output_tokens)}
            ${detailField("Total Tokens", item.token_usage.total_tokens)}
            ${detailField("Cached Input Tokens", item.token_usage.cached_input_tokens)}
            ${detailField("Estimated Input Size", item.token_usage.token_estimate)}
            ${detailField("Total Cost (USD)", formatUsd(item.token_usage.total_cost_usd))}
          </div>
        </div>

        <div class="detail-section">
          <h3>Trace</h3>
          <div class="detail-grid">
            ${detailField("Trace Id", item.trace_id)}
            ${detailField("Created At", item.created_at)}
            ${detailField("Month", item.month)}
            ${detailField("Legacy Token Estimate", item.token_estimate)}
          </div>
        </div>
      </section>
    </div>
  `;
}

function renderSearchInterpretation(plan) {
  if (!plan || !plan.used_llm) {
    searchSummary.textContent = "";
    return;
  }

  const inferredFields = [
    "garment_type",
    "style",
    "material",
    "color",
    "pattern",
    "occasion",
    "consumer_profile",
    "season",
    "designer",
    "continent",
    "country",
    "city",
    "year",
    "month",
  ]
    .filter((key) => plan[key] !== null && plan[key] !== undefined && plan[key] !== "")
    .map((key) => `${key.replaceAll("_", " ")}: ${plan[key]}`);

  const parts = [];
  if (plan.full_text_query) {
    parts.push(`text: ${plan.full_text_query}`);
  }
  if (inferredFields.length) {
    parts.push(`filters: ${inferredFields.join(", ")}`);
  }

  searchSummary.textContent = parts.length ? `LLM search parser -> ${parts.join(" | ")}` : "";
}

function buildSearchParams() {
  // Build the query string from the search box plus the current in-memory
  // filter state.
  const params = new URLSearchParams();
  const queryValue = document.querySelector("#search-query").value.trim();
  if (queryValue) {
    params.set("query", queryValue);
  }
  Object.entries(activeFilters).forEach(([key, value]) => {
    if (value) {
      params.set(key, value);
    }
  });
  return params;
}

async function loadFilters() {
  const response = await fetch("/api/filters");
  const filters = await response.json();
  renderFilters(filters);
}

async function loadLibrary(options = {}) {
  try {
    renderLibraryError("");
    const params = buildSearchParams();
    const url = `/api/garments${params.toString() ? `?${params.toString()}` : ""}`;
    const response = await fetch(url);
    const payload = await response.json();
    const items = Array.isArray(payload.items) ? payload.items : [];

    currentItems = items;
    renderCards(items);
    renderSearchInterpretation(payload.search_interpretation || null);

    try {
      ensureSelectedItem(options.selectedId);
      renderClassificationDetail();
      if (options.view) {
        setActiveView(options.view);
      }
    } catch (detailError) {
      console.error(detailError);
      renderLibraryError(`Detail view error: ${detailError.message}`);
    }
  } catch (error) {
    console.error(error);
    renderLibraryError(`Library load failed: ${error.message}`);
    resultsCount.textContent = "0 looks";
    cards.innerHTML = `<div class="empty">Could not render the library.</div>`;
  }
}

uploadForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  uploadStatus.textContent = "Uploading...";
  const formData = new FormData(uploadForm);
  const capturedAt = formData.get("captured_at");
  if (capturedAt) {
    // Normalize browser local time input into an ISO timestamp for the API.
    formData.set("captured_at", new Date(capturedAt).toISOString());
  }

  const response = await fetch("/api/garments/upload", {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const detail = await response.json();
    uploadStatus.textContent = detail.detail || "Upload failed.";
    return;
  }

  const uploadedItem = await response.json();
  uploadForm.reset();
  uploadStatus.textContent = "Classification complete.";
  document.querySelector("#search-query").value = "";
  Object.keys(activeFilters).forEach((key) => {
    activeFilters[key] = "";
  });
  await loadFilters();
  await loadLibrary({ selectedId: uploadedItem.id, view: "classification" });
});

searchForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  await loadLibrary();
});

document.querySelector("#search-query").addEventListener("input", () => {
  clearTimeout(searchDebounceTimer);
  searchDebounceTimer = setTimeout(() => {
    loadLibrary();
  }, 350);
});

filtersForm.addEventListener("change", async (event) => {
  const select = event.target.closest("select[data-filter-key]");
  if (!select) {
    return;
  }
  // Persist the selected value so future renders can restore the dropdown state.
  activeFilters[select.dataset.filterKey] = select.value;
  await loadLibrary();
});

cards.addEventListener("click", (event) => {
  const trigger = event.target.closest("[data-garment-id]");
  if (!trigger) {
    return;
  }
  selectedGarmentId = Number(trigger.dataset.garmentId);
  renderCards(currentItems);
  renderClassificationDetail();
  setActiveView("classification");
});

classificationDetail.addEventListener("submit", async (event) => {
  const form = event.target.closest(".annotation-form");
  if (!form) {
    return;
  }
  event.preventDefault();
  const garmentId = form.dataset.garmentId;
  const formData = new FormData(form);
  const payload = {
    note: formData.get("note"),
    // Tags are stored as a real array in the API even though the user types
    // them as a comma-separated string.
    tags: String(formData.get("tags") || "")
      .split(",")
      .map((value) => value.trim())
      .filter(Boolean),
  };
  const response = await fetch(`/api/garments/${garmentId}/annotations`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  if (response.ok) {
    await loadLibrary({ selectedId: garmentId, view: "classification" });
  }
});

viewTabs.forEach((button) => {
  button.addEventListener("click", () => {
    setActiveView(button.dataset.view);
  });
});

// Initial page load: fetch filter options first, then render the library.
loadFilters()
  .then(() => loadLibrary())
  .catch((error) => {
    console.error(error);
    renderLibraryError(`Startup error: ${error.message}`);
  });
