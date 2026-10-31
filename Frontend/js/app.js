const state = {
  results: [],
  selected: null,
  selectedIds: [],
  user: null,
};

const $ = (id) => document.getElementById(id);

function money(v) {
  if (v == null || v === "") return "—";
  const n = Number(v);
  if (Number.isNaN(n)) return String(v);
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(n);
}

function showView(name) {
  document.querySelectorAll("[data-view]").forEach((el) => {
    el.classList.toggle("hidden", el.dataset.view !== name);
  });
  document.querySelectorAll(".nav button").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.nav === name);
  });
}

function addChat(text, who) {
  const log = $("chatLog");
  const div = document.createElement("div");
  div.className = `bubble ${who}`;
  div.textContent = text;
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
}

function renderResults(results) {
  state.results = results || [];
  const grid = $("results");
  grid.innerHTML = "";
  if (!state.results.length) {
    grid.innerHTML = `<div class="panel muted">No listings matched these hard constraints. Try relaxing budget or locality.</div>`;
    return;
  }
  state.results.forEach((p) => {
    const el = document.createElement("article");
    el.className = "card";
    const price = p.purpose === "rent" ? `${money(p.monthly_rent)} / mo` : money(p.asking_price);
    el.innerHTML = `
      <h3>${p.title}</h3>
      <div class="meta">${p.configuration} · ${p.property_type} · ${p.locality}${p.city ? `, ${p.city}` : ""}</div>
      <div class="price">${price}</div>
      <div class="tags">${(p.match_reasons || []).slice(0, 3).map((r) => `<span class="tag">${r}</span>`).join("")}</div>
    `;
    el.onclick = () => openProperty(p.id);
    grid.appendChild(el);
  });
}

async function openProperty(id) {
  showView("discover");
  const detail = await EstateAPI.getProperty(id);
  state.selected = detail;
  if (!state.selectedIds.includes(id)) {
    state.selectedIds = [...state.selectedIds, id].slice(-4);
  }
  const price = detail.purpose === "rent" ? money(detail.monthly_rent) : money(detail.asking_price);
  const area = detail.area?.value
    ? `${detail.area.value} ${detail.area.unit} (${detail.area.basis})`
    : "Area not disclosed";
  $("detail").innerHTML = `
    <h2>${detail.title}</h2>
    <p class="meta">${detail.address}</p>
    <p class="price">${price} · ${detail.configuration} · ${area}</p>
    <p>${detail.description || ""}</p>
    <div class="tags">${(detail.amenities_tags || []).map((t) => `<span class="tag">${t}</span>`).join("")}</div>
    ${(detail.limitations || []).length ? `<div class="limitations"><strong>Limitations:</strong> ${detail.limitations.join(" ")}</div>` : ""}
    <div class="actions">
      <button class="btn primary" id="btnNeighbourhood">Neighbourhood</button>
      <button class="btn" id="btnPrice">Price analysis</button>
      <button class="btn" id="btnYield">Yield estimate</button>
      <button class="btn" id="btnEnquire">Enquire</button>
      <button class="btn ghost" id="btnCompareAdd">Use in AI compare (${state.selectedIds.length}/4)</button>
    </div>
    <div id="detailExtra" class="muted" style="margin-top:12px"></div>
  `;
  $("btnNeighbourhood").onclick = async () => {
    const n = await EstateAPI.getNeighbourhood(id);
    const list = (n.amenities || []).slice(0, 8).map((a) =>
      `<li>${a.name} · ${a.category} · ~${Math.round(a.distance.value)}m (${a.distance.method})</li>`
    ).join("");
    $("detailExtra").innerHTML = `
      <strong>Coverage:</strong> ${n.coverage}<br/>
      <ul>${list || "<li>No amenities in radius</li>"}</ul>
      <div class="limitations">${(n.limitations || []).join(" ")}</div>
    `;
  };
  $("btnPrice").onclick = async () => {
    const p = await EstateAPI.getPriceAnalysis(id);
    $("detailExtra").innerHTML = `
      <div>Price/sqft: <strong>${p.asking_price_per_sq_ft ?? "n/a"}</strong> (${p.area_basis || "unknown basis"})</div>
      <div>Formula: ${p.formula || "n/a"}</div>
      <div>Benchmark confidence: ${p.benchmark?.confidence} · sample ${p.benchmark?.sample_size ?? 0}</div>
      <div class="limitations">${(p.limitations || []).join(" ")}</div>
    `;
  };
  $("btnYield").onclick = async () => {
    const purchase = Number(detail.asking_price);
    const rent = Number(detail.monthly_rent || prompt("Expected monthly rent (INR)?", "25000"));
    if (!purchase || !rent) {
      $("detailExtra").textContent = "Need purchase price and monthly rent for yield calculation.";
      return;
    }
    const y = await EstateAPI.calculateInvestment({
      purchase_price: purchase,
      monthly_rent: rent,
      property_id: id,
    });
    $("detailExtra").innerHTML = `
      <div>Gross yield: <strong>${y.gross_yield_pct}%</strong> · Net yield: <strong>${y.net_yield_pct}%</strong></div>
      <div>Acquisition cost: ${money(y.total_acquisition_cost)}</div>
      <div class="limitations">${y.disclaimer} ${(y.limitations || []).join(" ")}</div>
    `;
  };
  $("btnEnquire").onclick = () => {
    $("enquiryListingId").value = detail.listing_id;
    $("enquiryPanel").classList.remove("hidden");
  };
  $("btnCompareAdd").onclick = () => {
    addChat(`Selected for compare: ${detail.title} (${id})`, "agent");
  };
}

async function runSearch() {
  const params = {
    purpose: $("fPurpose").value,
    city: $("fCity").value,
    locality: $("fLocality").value,
    bedrooms: $("fBeds").value,
    min_price: $("fMin").value,
    max_price: $("fMax").value,
    page_size: 20,
  };
  $("resultsStatus").textContent = "Searching…";
  try {
    const data = await EstateAPI.searchProperties(params);
    renderResults(data.results);
    $("resultsStatus").textContent = `${data.pagination.total} listings`;
  } catch (e) {
    $("resultsStatus").textContent = e.message;
  }
}

async function runAISearch() {
  const query = $("aiQuery").value.trim();
  if (!query) return;
  addChat(query, "user");
  try {
    const data = await EstateAPI.aiSearch(query);
    addChat(
      `${data.explanation}\nFilters: ${JSON.stringify(data.search_specification, null, 2)}\nMatches: ${data.results.length}`,
      "agent"
    );
    if (data.results?.length) renderResults(data.results);
    if (data.clarification_required) {
      addChat((data.clarification_questions || []).join("\n"), "agent");
    }
  } catch (e) {
    addChat(e.message, "agent");
  }
}

async function runAIChat() {
  const message = $("chatInput").value.trim();
  if (!message) return;
  $("chatInput").value = "";
  addChat(message, "user");
  try {
    const data = await EstateAPI.aiChat({
      message,
      property_ids: state.selected ? [state.selected.id] : state.selectedIds,
    });
    addChat(data.answer, "agent");
    if (data.limitations?.length) addChat(`Limitations: ${data.limitations.join(" ")}`, "agent");
  } catch (e) {
    addChat(e.message, "agent");
  }
}

async function submitEnquiry(e) {
  e.preventDefault();
  try {
    const lead = await EstateAPI.createLead({
      listing_id: $("enquiryListingId").value,
      message: $("enquiryMessage").value,
      contact_preference: "phone",
      requester_name: $("enquiryName").value,
      requester_phone: $("enquiryPhone").value,
      requester_email: $("enquiryEmail").value,
      idempotency_key: crypto.randomUUID(),
    });
    $("enquiryStatus").textContent = `Enquiry submitted (${lead.id}).`;
    $("enquiryPanel").classList.add("hidden");
  } catch (err) {
    $("enquiryStatus").textContent = err.message;
  }
}

async function doLogin(e) {
  e.preventDefault();
  try {
    const tok = await EstateAPI.login($("loginEmail").value, $("loginPassword").value);
    localStorage.setItem("estateai_token", tok.access_token);
    await refreshUser();
    showView("discover");
  } catch (err) {
    $("authStatus").textContent = err.message;
  }
}

async function doRegister(e) {
  e.preventDefault();
  try {
    const tok = await EstateAPI.register({
      email: $("regEmail").value,
      password: $("regPassword").value,
      full_name: $("regName").value,
      role: $("regRole").value,
    });
    localStorage.setItem("estateai_token", tok.access_token);
    await refreshUser();
    showView("discover");
  } catch (err) {
    $("authStatus").textContent = err.message;
  }
}

async function refreshUser() {
  try {
    if (!localStorage.getItem("estateai_token")) {
      state.user = null;
      $("userPill").textContent = "Browsing as guest";
      return;
    }
    state.user = await EstateAPI.me();
    $("userPill").textContent = `${state.user.full_name || state.user.email} · ${state.user.roles.join(", ")}`;
  } catch {
    localStorage.removeItem("estateai_token");
    $("userPill").textContent = "Browsing as guest";
  }
}

function wire() {
  document.querySelectorAll("[data-nav]").forEach((btn) => {
    btn.onclick = () => showView(btn.dataset.nav);
  });
  $("searchBtn").onclick = runSearch;
  $("aiSearchBtn").onclick = runAISearch;
  $("chatSendBtn").onclick = runAIChat;
  $("chatInput").addEventListener("keydown", (e) => {
    if (e.key === "Enter") runAIChat();
  });
  $("enquiryForm").addEventListener("submit", submitEnquiry);
  $("loginForm").addEventListener("submit", doLogin);
  $("registerForm").addEventListener("submit", doRegister);
  $("logoutBtn").onclick = () => {
    localStorage.removeItem("estateai_token");
    refreshUser();
  };
}

window.addEventListener("DOMContentLoaded", async () => {
  wire();
  await refreshUser();
  showView("discover");
  await runSearch();
  addChat("Ask me to find a 2BHK under ₹80 lakh in Gurugram or Noida, or select a property for neighbourhood / yield questions.", "agent");
});
