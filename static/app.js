// State
let currentUser = null;
let currentTab = "home";
let cachedBusinesses = [];
let cachedAlumni = [];

// DOM Ready
document.addEventListener("DOMContentLoaded", () => {
  checkAuth();
  loadAnnouncements();
  setupDemoQuickSwitch();
});

// Utilities
function showToast(message, type = "info") {
  const container = document.getElementById("toastContainer");
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.innerText = message;
  container.appendChild(toast);
  setTimeout(() => {
    toast.remove();
  }, 4000);
}

function openModal(id) {
  const m = document.getElementById(id);
  if (m) m.classList.add("active");
}

function closeModal(id) {
  const m = document.getElementById(id);
  if (m) m.classList.remove("active");
}

// Tab Switching
function switchTab(tabName) {
  currentTab = tabName;
  document.querySelectorAll(".tab-pane").forEach(p => p.classList.remove("active"));
  document.querySelectorAll(".nav-tabs button").forEach(b => b.classList.remove("active"));

  const targetPane = document.getElementById(`tab-${tabName}`);
  const targetBtn = document.getElementById(`btnTab-${tabName}`);
  if (targetPane) targetPane.classList.add("active");
  if (targetBtn) targetBtn.classList.add("active");

  // Load relevant data on tab entry
  if (tabName === "alumni") loadAlumni();
  else if (tabName === "businesses") loadBusinesses();
  else if (tabName === "products") loadProducts();
  else if (tabName === "mentors") loadMentors();
  else if (tabName === "classes") loadClasses();
  else if (tabName === "incubation") loadIncubation();
  else if (tabName === "leads") loadLeads();
  else if (tabName === "pks") loadPks();
  else if (tabName === "dashboard") loadKpiData();
  else if (tabName === "pdp") loadPdp();
}

// Authentication
async function checkAuth() {
  try {
    const res = await fetch("/api/auth/me");
    const data = await res.json();
    if (data.is_demo) {
      document.getElementById("demoBanner").style.display = "flex";
    }

    if (data.logged_in && data.user) {
      currentUser = data.user;
      renderAuthUser(currentUser);
    } else {
      currentUser = null;
      renderAuthGuest();
    }
  } catch (e) {
    console.error("Auth check failed:", e);
    renderAuthGuest();
  }
}

function renderAuthUser(user) {
  document.getElementById("guestNav").style.display = "none";
  const userInfo = document.getElementById("userInfo");
  userInfo.style.display = "flex";
  document.getElementById("userName").innerText = user.full_name;

  const roleBadge = document.getElementById("userBadgeRole");
  roleBadge.innerText = user.role.toUpperCase();
  if (user.role === "admin") {
    roleBadge.className = "badge badge-danger";
    document.getElementById("btnCreateClass").style.display = "inline-flex";
    document.getElementById("btnNewAnnouncement").style.display = "inline-flex";
    document.getElementById("adminQueuesSection").style.display = "block";
  } else {
    roleBadge.className = "badge badge-info";
    document.getElementById("btnCreateClass").style.display = "none";
    document.getElementById("btnNewAnnouncement").style.display = "none";
    document.getElementById("adminQueuesSection").style.display = "none";
  }
}

function renderAuthGuest() {
  document.getElementById("guestNav").style.display = "flex";
  document.getElementById("userInfo").style.display = "none";
  document.getElementById("btnCreateClass").style.display = "none";
  document.getElementById("btnNewAnnouncement").style.display = "none";
  document.getElementById("adminQueuesSection").style.display = "none";
}

function openAuthModal(subTab = "login") {
  openModal("modalAuth");
  showAuthSubTab(subTab);
}

function showAuthSubTab(subTab) {
  const formLogin = document.getElementById("formLogin");
  const formRegister = document.getElementById("formRegister");
  const btnLogin = document.getElementById("authTabLoginBtn");
  const btnReg = document.getElementById("authTabRegisterBtn");
  const title = document.getElementById("authModalTitle");

  if (subTab === "login") {
    formLogin.style.display = "block";
    formRegister.style.display = "none";
    btnLogin.className = "btn btn-primary btn-sm";
    btnReg.className = "btn btn-light btn-sm";
    title.innerText = "Masuk ke Akun Anda";
  } else {
    formLogin.style.display = "none";
    formRegister.style.display = "block";
    btnLogin.className = "btn btn-light btn-sm";
    btnReg.className = "btn btn-primary btn-sm";
    title.innerText = "Formulir Pendaftaran Alumni Baru";
  }
}

async function submitLogin(e) {
  e.preventDefault();
  const email = document.getElementById("loginEmail").value;
  const password = document.getElementById("loginPassword").value;

  try {
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password })
    });
    const data = await res.json();
    if (res.ok) {
      showToast(data.message, "success");
      closeModal("modalAuth");
      await checkAuth();
      switchTab(currentTab);
    } else {
      showToast(data.message || "Gagal masuk", "error");
    }
  } catch (err) {
    showToast("Kesalahan koneksi ke server", "error");
  }
}

async function submitRegister(e) {
  e.preventDefault();
  const payload = {
    email: document.getElementById("regEmail").value,
    password: document.getElementById("regPassword").value,
    full_name: document.getElementById("regName").value,
    nim: document.getElementById("regNim").value,
    faculty: document.getElementById("regFaculty").value,
    graduation_year: document.getElementById("regGradYear").value,
    profession: document.getElementById("regProfession").value,
    company: document.getElementById("regCompany").value,
    city: document.getElementById("regCity").value,
    phone: document.getElementById("regPhone").value,
    linkedin: document.getElementById("regLinkedin").value,
    bio: document.getElementById("regBio").value,
    consent_data: document.getElementById("regConsent").checked ? 1 : 0
  };

  try {
    const res = await fetch("/api/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (res.ok) {
      showToast(data.message, "success");
      closeModal("modalAuth");
      await checkAuth();
      switchTab("home");
    } else {
      showToast(data.message || "Gagal mendaftar", "error");
    }
  } catch (err) {
    showToast("Kesalahan koneksi ke server", "error");
  }
}

async function handleLogout() {
  try {
    await fetch("/api/auth/logout", { method: "POST" });
    showToast("Anda telah keluar.", "info");
    await checkAuth();
    switchTab("home");
  } catch (e) {
    console.error(e);
  }
}

function setupDemoQuickSwitch() {
  const sel = document.getElementById("demoQuickSwitch");
  if (!sel) return;
  sel.addEventListener("change", async () => {
    const email = sel.value;
    if (!email) return;
    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password: "DemoMaliki2026!" })
      });
      if (res.ok) {
        showToast(`Beralih ke akun demo: ${email}`, "success");
        await checkAuth();
        switchTab(currentTab);
      }
    } catch (e) {
      showToast("Gagal berganti akun demo", "error");
    }
  });
}

// Profile Modal
function openProfileModal() {
  if (!currentUser) return;
  document.getElementById("profName").value = currentUser.full_name || "";
  document.getElementById("profProfession").value = currentUser.profession || "";
  document.getElementById("profCompany").value = currentUser.company || "";
  document.getElementById("profProvince").value = currentUser.province || "";
  document.getElementById("profCity").value = currentUser.city || "";
  document.getElementById("profPhone").value = currentUser.phone || "";
  document.getElementById("profLinkedin").value = currentUser.linkedin || "";
  document.getElementById("profBio").value = currentUser.bio || "";
  openModal("modalProfile");
}

async function submitProfileUpdate(e) {
  e.preventDefault();
  const payload = {
    full_name: document.getElementById("profName").value,
    profession: document.getElementById("profProfession").value,
    company: document.getElementById("profCompany").value,
    province: document.getElementById("profProvince").value,
    city: document.getElementById("profCity").value,
    phone: document.getElementById("profPhone").value,
    linkedin: document.getElementById("profLinkedin").value,
    bio: document.getElementById("profBio").value,
  };

  try {
    const res = await fetch("/api/auth/profile", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (res.ok) {
      showToast(data.message, "success");
      closeModal("modalProfile");
      await checkAuth();
    } else {
      showToast(data.message || "Gagal memperbarui profil", "error");
    }
  } catch (err) {
    showToast("Kesalahan server", "error");
  }
}

// Announcements
async function loadAnnouncements() {
  try {
    const res = await fetch("/api/announcements");
    const data = await res.json();
    const container = document.getElementById("announcementList");
    if (!data.announcements || data.announcements.length === 0) {
      container.innerHTML = `<p style="color: var(--text-muted); font-size: 0.9rem;">Belum ada pengumuman terbaru.</p>`;
      return;
    }
    container.innerHTML = data.announcements.map(a => `
      <div style="border-bottom: 1px solid var(--border); padding: 12px 0;">
        <div style="display: flex; gap: 8px; align-items: center; margin-bottom: 4px;">
          <span class="badge ${a.category === 'event' ? 'badge-success' : 'badge-info'}">${a.category.toUpperCase()}</span>
          <strong style="font-size: 0.95rem; color: var(--primary);">${a.title}</strong>
        </div>
        <p style="font-size: 0.88rem; color: var(--text-main); margin-bottom: 4px;">${a.content}</p>
        <span style="font-size: 0.75rem; color: var(--text-muted);">${a.created_at}</span>
      </div>
    `).join("");
  } catch (e) {
    console.error(e);
  }
}

function openAnnouncementModal() {
  openModal("modalAnnouncement");
}

async function submitAnnouncement(e) {
  e.preventDefault();
  const payload = {
    title: document.getElementById("annTitle").value,
    content: document.getElementById("annContent").value,
    category: document.getElementById("annCategory").value,
  };
  try {
    const res = await fetch("/api/announcements", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (res.ok) {
      showToast(data.message, "success");
      closeModal("modalAnnouncement");
      loadAnnouncements();
    }
  } catch (err) {
    showToast("Gagal menyimpan pengumuman", "error");
  }
}

// Alumni Directory
async function loadAlumni() {
  const q = document.getElementById("filterAlumniQ").value;
  const faculty = document.getElementById("filterAlumniFaculty").value;
  const city = document.getElementById("filterAlumniCity").value;

  const params = new URLSearchParams();
  if (q) params.set("q", q);
  if (faculty) params.set("faculty", faculty);
  if (city) params.set("city", city);

  try {
    const res = await fetch(`/api/alumni?${params.toString()}`);
    const data = await res.json();
    cachedAlumni = data.alumni || [];
    renderAlumniGrid(cachedAlumni);
  } catch (e) {
    console.error(e);
  }
}

function renderAlumniGrid(list) {
  const grid = document.getElementById("alumniGrid");
  if (!list || list.length === 0) {
    grid.innerHTML = `<div style="grid-column: 1/-1; padding: 20px; text-align: center; color: var(--text-muted);">Tidak ada data alumni yang cocok dengan pencarian.</div>`;
    return;
  }
  grid.innerHTML = list.map(a => `
    <div class="card">
      <div class="card-header">
        <strong style="font-size: 1.05rem; color: var(--primary);">${a.full_name}</strong>
        <span class="badge ${a.status === 'approved' ? 'badge-success' : 'badge-warning'}">${a.status}</span>
      </div>
      <p style="font-size: 0.85rem; font-weight: 600; color: var(--text-main); margin-bottom: 4px;">
        ${a.profession || "Alumni"} ${a.company ? "at " + a.company : ""}
      </p>
      <p style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 8px;">
        Fakultas ${a.faculty || "-"} • Lulus ${a.graduation_year || "-"} • ${a.city || "Indonesia"}
      </p>
      <p style="font-size: 0.82rem; color: var(--text-muted); margin-bottom: 12px; line-height: 1.4;">
        ${a.bio || "Belum ada bio singkat."}
      </p>
      <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid var(--border); padding-top: 8px;">
        ${a.linkedin ? `<a href="${a.linkedin}" target="_blank" rel="noopener" class="btn btn-outline-primary btn-sm">Profil LinkedIn</a>` : `<span></span>`}
        ${currentUser && currentUser.role === 'admin' && a.status === 'pending' ? `
          <button class="btn btn-primary btn-sm" onclick="verifyAlumni(${a.id}, 'approved')">Verifikasi</button>
        ` : ''}
      </div>
    </div>
  `).join("");
}

async function verifyAlumni(userId, status) {
  try {
    const res = await fetch("/api/alumni/verify", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: userId, status })
    });
    const data = await res.json();
    showToast(data.message, "success");
    loadAlumni();
    loadKpiData();
  } catch (e) {
    showToast("Gagal memverifikasi alumni", "error");
  }
}

// Businesses
async function loadBusinesses() {
  const q = document.getElementById("filterBizQ").value;
  const sector = document.getElementById("filterBizSector").value;
  const city = document.getElementById("filterBizCity").value;

  const params = new URLSearchParams();
  if (q) params.set("q", q);
  if (sector) params.set("sector", sector);
  if (city) params.set("city", city);

  try {
    const res = await fetch(`/api/businesses?${params.toString()}`);
    const data = await res.json();
    cachedBusinesses = data.businesses || [];
    renderBusinessesGrid(cachedBusinesses);
  } catch (e) {
    console.error(e);
  }
}

function renderBusinessesGrid(list) {
  const grid = document.getElementById("businessesGrid");
  if (!list || list.length === 0) {
    grid.innerHTML = `<div style="grid-column: 1/-1; padding: 20px; text-align: center; color: var(--text-muted);">Belum ada profil usaha yang terdaftar atau sesuai kriteria.</div>`;
    return;
  }
  grid.innerHTML = list.map(b => `
    <div class="card">
      <div class="card-header">
        <strong style="font-size: 1.05rem; color: var(--primary);">${b.name}</strong>
        <span class="badge ${b.is_curated ? 'badge-success' : 'badge-warning'}">${b.is_curated ? 'Terkurasi' : 'Menunggu Kurasi'}</span>
      </div>
      <p style="font-size: 0.8rem; font-weight: 700; color: var(--secondary); margin-bottom: 6px;">${b.sector}</p>
      <p style="font-size: 0.85rem; color: var(--text-main); margin-bottom: 8px;">${b.description || "-"}</p>
      <p style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 12px;">
        📍 ${b.city || ""}, ${b.province || ""} • Pemilik: <strong>${b.owner_name}</strong>
      </p>
      <div style="display: flex; gap: 8px; flex-wrap: wrap; border-top: 1px solid var(--border); padding-top: 10px;">
        <button class="btn btn-secondary btn-sm" onclick="openSendLeadModal(${b.id}, '${escapeHtml(b.name)}')">Kirim Peluang Bisnis</button>
        ${b.contact_wa ? `<a href="https://wa.me/${cleanPhone(b.contact_wa)}" target="_blank" class="btn btn-light btn-sm">WhatsApp</a>` : ''}
        ${b.website ? `<a href="${b.website}" target="_blank" rel="noopener" class="btn btn-light btn-sm">Web</a>` : ''}
        ${currentUser && currentUser.role === 'admin' ? `
          <button class="btn btn-outline-primary btn-sm" onclick="curateBusiness(${b.id}, ${b.is_curated ? 0 : 1})">${b.is_curated ? 'Batal Kurasi' : 'Kurasi'}</button>
        ` : ''}
      </div>
    </div>
  `).join("");
}

function openBusinessModal() {
  if (!currentUser) {
    openAuthModal('login');
    showToast("Silakan masuk terlebih dahulu untuk mendaftarkan usaha.", "warning");
    return;
  }
  openModal("modalBusiness");
}

async function submitBusiness(e) {
  e.preventDefault();
  const payload = {
    name: document.getElementById("bizName").value,
    sector: document.getElementById("bizSector").value,
    description: document.getElementById("bizDescription").value,
    province: document.getElementById("bizProvince").value,
    city: document.getElementById("bizCity").value,
    address: document.getElementById("bizAddress").value,
    website: document.getElementById("bizWebsite").value,
    contact_wa: document.getElementById("bizWa").value,
  };

  try {
    const res = await fetch("/api/businesses", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (res.ok) {
      showToast(data.message, "success");
      closeModal("modalBusiness");
      loadBusinesses();
      loadKpiData();
    } else {
      showToast(data.message, "error");
    }
  } catch (err) {
    showToast("Kesalahan server", "error");
  }
}

async function curateBusiness(bizId, isCurated) {
  try {
    const res = await fetch("/api/businesses/curate", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ business_id: bizId, is_curated: isCurated })
    });
    const data = await res.json();
    showToast(data.message, "success");
    loadBusinesses();
    loadKpiData();
  } catch (e) {
    showToast("Gagal kurasi usaha", "error");
  }
}

// Products Catalog
async function loadProducts() {
  const q = document.getElementById("filterProdQ").value;
  const cat = document.getElementById("filterProdCat").value;

  const params = new URLSearchParams();
  if (q) params.set("q", q);
  if (cat) params.set("category", cat);

  try {
    const res = await fetch(`/api/products?${params.toString()}`);
    const data = await res.json();
    renderProductsGrid(data.products || []);
  } catch (e) {
    console.error(e);
  }
}

function renderProductsGrid(list) {
  const grid = document.getElementById("productsGrid");
  if (!list || list.length === 0) {
    grid.innerHTML = `<div style="grid-column: 1/-1; padding: 20px; text-align: center; color: var(--text-muted);">Belum ada produk atau jasa terkurasi dalam katalog.</div>`;
    return;
  }
  grid.innerHTML = list.map(p => `
    <div class="card" style="display: flex; flex-direction: column;">
      ${p.photo_url ? `<img src="${p.photo_url}" alt="${p.name}" style="width: 100%; height: 160px; object-fit: cover; border-radius: var(--radius-sm); margin-bottom: 10px;">` : ''}
      <div class="card-header" style="margin-bottom: 6px;">
        <strong style="font-size: 1rem; color: var(--primary);">${p.name}</strong>
        <span class="badge ${p.is_curated ? 'badge-success' : 'badge-warning'}">${p.is_curated ? 'Terkurasi' : 'Draf'}</span>
      </div>
      <p style="font-size: 0.8rem; font-weight: 700; color: var(--secondary);">${p.category} • ${p.business_name}</p>
      <p style="font-size: 0.85rem; color: var(--text-main); margin: 6px 0; flex: 1;">${p.description || "-"}</p>
      <p style="font-size: 1.1rem; font-weight: 800; color: var(--primary); margin-bottom: 8px;">
        ${p.price > 0 ? "Rp " + Number(p.price).toLocaleString("id-ID") : "Hubungi Pemilik"}
      </p>
      <div style="display: flex; gap: 8px; border-top: 1px solid var(--border); padding-top: 10px; flex-wrap: wrap;">
        ${p.ref_link ? `<a href="${p.ref_link}" target="_blank" rel="noopener" class="btn btn-secondary btn-sm" style="flex: 1;">Brosur / Beli</a>` : ''}
        ${p.contact_wa ? `<a href="https://wa.me/${cleanPhone(p.contact_wa)}" target="_blank" class="btn btn-light btn-sm">WhatsApp</a>` : ''}
        ${currentUser && currentUser.role === 'admin' ? `
          <button class="btn btn-outline-primary btn-sm" onclick="curateProduct(${p.id}, ${p.is_curated ? 0 : 1})">${p.is_curated ? 'Batal' : 'Kurasi'}</button>
        ` : ''}
        ${currentUser && (currentUser.role === 'admin' || currentUser.id === p.owner_id) ? `
          <button class="btn btn-danger btn-sm" onclick="deleteProduct(${p.id}, '${escapeHtml(p.name)}')">Hapus</button>
        ` : ''}
      </div>
    </div>
  `).join("");
}

async function deleteProduct(prodId, prodName) {
  if (!confirm(`Apakah Anda yakin ingin menghapus produk "${prodName}" dari katalog?`)) return;
  try {
    const res = await fetch("/api/products/delete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ product_id: prodId })
    });
    const data = await res.json();
    if (res.ok) {
      showToast(data.message, "success");
      loadProducts();
      loadKpiData();
    } else {
      showToast(data.message || "Gagal menghapus produk", "error");
    }
  } catch (e) {
    showToast("Kesalahan server saat menghapus produk", "error");
  }
}

async function openProductModal() {
  if (!currentUser) {
    openAuthModal('login');
    showToast("Silakan masuk untuk menambah produk/jasa.", "warning");
    return;
  }
  // Load businesses owned by user or all for admin
  try {
    const res = await fetch("/api/businesses");
    const data = await res.json();
    const sel = document.getElementById("prodBusinessId");
    sel.innerHTML = (data.businesses || []).map(b => `<option value="${b.id}">${b.name} (${b.sector})</option>`).join("");
    if (!data.businesses || data.businesses.length === 0) {
      showToast("Anda harus memiliki profil usaha sebelum menambah produk.", "warning");
      openBusinessModal();
      return;
    }
    openModal("modalProduct");
  } catch (e) {
    console.error(e);
  }
}

async function submitProduct(e) {
  e.preventDefault();
  const payload = {
    business_id: document.getElementById("prodBusinessId").value,
    name: document.getElementById("prodName").value,
    category: document.getElementById("prodCategory").value,
    price: document.getElementById("prodPrice").value,
    description: document.getElementById("prodDescription").value,
    photo_url: document.getElementById("prodPhotoUrl").value,
    ref_link: document.getElementById("prodRefLink").value,
  };

  try {
    const res = await fetch("/api/products", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (res.ok) {
      showToast(data.message, "success");
      closeModal("modalProduct");
      loadProducts();
      loadKpiData();
    } else {
      showToast(data.message, "error");
    }
  } catch (err) {
    showToast("Kesalahan server", "error");
  }
}

async function curateProduct(prodId, isCurated) {
  try {
    const res = await fetch("/api/products/curate", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ product_id: prodId, is_curated: isCurated })
    });
    const data = await res.json();
    showToast(data.message, "success");
    loadProducts();
    loadKpiData();
  } catch (e) {
    showToast("Gagal kurasi produk", "error");
  }
}

// Mentors
async function loadMentors() {
  try {
    const res = await fetch("/api/mentors");
    const data = await res.json();
    renderMentorsGrid(data.mentors || []);
  } catch (e) {
    console.error(e);
  }
}

function renderMentorsGrid(list) {
  const grid = document.getElementById("mentorsGrid");
  if (!list || list.length === 0) {
    grid.innerHTML = `<div style="grid-column: 1/-1; padding: 20px; text-align: center; color: var(--text-muted);">Belum ada mentor aktif terdaftar.</div>`;
    return;
  }
  grid.innerHTML = list.map(m => `
    <div class="card">
      <div class="card-header">
        <div>
          <strong style="font-size: 1.1rem; color: var(--primary);">${m.full_name}</strong>
          <p style="font-size: 0.8rem; color: var(--text-muted);">${m.profession || "Mentor"} ${m.company ? "at " + m.company : ""}</p>
        </div>
        <span class="badge ${m.status === 'approved' ? 'badge-success' : 'badge-warning'}">${m.status}</span>
      </div>
      <div style="background-color: var(--primary-light); padding: 8px 12px; border-radius: var(--radius-sm); margin-bottom: 10px;">
        <strong style="font-size: 0.85rem; color: var(--primary);">Bidang Keahlian:</strong>
        <p style="font-size: 0.85rem; color: var(--primary-hover); font-weight: 600;">${m.expertise}</p>
      </div>
      <p style="font-size: 0.85rem; color: var(--text-main); margin-bottom: 8px;">${m.bio || "-"}</p>
      <p style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 12px;">Pengalaman: ${m.years_experience} Tahun • Domisili: ${m.city || "Indonesia"}</p>
      <div style="display: flex; gap: 8px; border-top: 1px solid var(--border); padding-top: 8px;">
        ${m.portfolio_url ? `<a href="${m.portfolio_url}" target="_blank" rel="noopener" class="btn btn-light btn-sm">Portofolio</a>` : ''}
        ${m.linkedin ? `<a href="${m.linkedin}" target="_blank" rel="noopener" class="btn btn-outline-primary btn-sm">LinkedIn</a>` : ''}
        ${currentUser && currentUser.role === 'admin' ? `
          <button class="btn btn-primary btn-sm" onclick="reviewMentor(${m.id}, '${m.status === 'approved' ? 'pending' : 'approved'}')">
            ${m.status === 'approved' ? 'Tangguhkan' : 'Setujui Mentor'}
          </button>
        ` : ''}
      </div>
    </div>
  `).join("");
}

function openMentorModal() {
  if (!currentUser) {
    openAuthModal('login');
    showToast("Silakan masuk terlebih dahulu untuk mengajukan diri sebagai mentor.", "warning");
    return;
  }
  openModal("modalMentor");
}

async function submitMentorApply(e) {
  e.preventDefault();
  const payload = {
    expertise: document.getElementById("mentorExpertise").value,
    years_experience: document.getElementById("mentorYears").value,
    bio: document.getElementById("mentorBio").value,
    portfolio_url: document.getElementById("mentorPortfolioUrl").value,
  };

  try {
    const res = await fetch("/api/mentors/apply", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (res.ok) {
      showToast(data.message, "success");
      closeModal("modalMentor");
      loadMentors();
      loadKpiData();
    } else {
      showToast(data.message, "error");
    }
  } catch (err) {
    showToast("Kesalahan server", "error");
  }
}

async function reviewMentor(mentorId, status) {
  try {
    const res = await fetch("/api/mentors/review", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mentor_id: mentorId, status })
    });
    const data = await res.json();
    showToast(data.message, "success");
    loadMentors();
    loadKpiData();
  } catch (e) {
    showToast("Gagal mengubah status mentor", "error");
  }
}

// Classes / Academy
async function loadClasses() {
  try {
    const res = await fetch("/api/classes");
    const data = await res.json();
    renderClassesGrid(data.classes || []);
  } catch (e) {
    console.error(e);
  }
}

function renderClassesGrid(list) {
  const grid = document.getElementById("classesGrid");
  if (!list || list.length === 0) {
    grid.innerHTML = `<div style="grid-column: 1/-1; padding: 20px; text-align: center; color: var(--text-muted);">Belum ada kelas pelatihan dibuka.</div>`;
    return;
  }
  grid.innerHTML = list.map(c => `
    <div class="card">
      <div class="card-header">
        <strong style="font-size: 1.1rem; color: var(--primary);">${c.title}</strong>
        <span class="badge ${c.is_open ? 'badge-success' : 'badge-danger'}">${c.is_open ? 'Buka Pendaftaran' : 'Tutup'}</span>
      </div>
      <p style="font-size: 0.85rem; font-weight: 600; color: var(--secondary); margin-bottom: 4px;">Instruktur: ${c.instructor}</p>
      <p style="font-size: 0.82rem; color: var(--text-muted); margin-bottom: 8px;">
        🗓 ${c.schedule || "Jadwal akan diumumkan"} • 📍 ${c.location || "Online"}
      </p>
      <p style="font-size: 0.85rem; color: var(--text-main); margin-bottom: 12px;">${c.description || "-"}</p>
      <div style="background: #f8fafc; padding: 8px 12px; border-radius: var(--radius-sm); margin-bottom: 12px; display: flex; justify-content: space-between; font-size: 0.82rem;">
        <span>Terdaftar: <strong>${c.enrolled_count} / ${c.quota}</strong> peserta</span>
        ${c.is_enrolled ? `<span class="badge badge-success">Terdaftar</span>` : ''}
      </div>
      <div style="display: flex; gap: 8px; justify-content: space-between; align-items: center; border-top: 1px solid var(--border); padding-top: 10px;">
        ${c.is_enrolled ? `
          <div>
            ${c.enrollment_info && c.enrollment_info.is_graduated ? `
              <span class="badge badge-success">Lulus: ${c.enrollment_info.certificate_num}</span>
            ` : `<span class="badge badge-info">Status: Sedang Mengikuti</span>`}
          </div>
        ` : `
          <button class="btn btn-primary btn-sm" onclick="enrollClass(${c.id})" ${!c.is_open || c.enrolled_count >= c.quota ? 'disabled' : ''}>
            Daftar Kelas Ini
          </button>
        `}
      </div>
    </div>
  `).join("");
}

function openCreateClassModal() {
  openModal("modalCreateClass");
}

async function submitCreateClass(e) {
  e.preventDefault();
  const payload = {
    title: document.getElementById("classTitle").value,
    instructor: document.getElementById("classInstructor").value,
    schedule: document.getElementById("classSchedule").value,
    location: document.getElementById("classLocation").value,
    quota: document.getElementById("classQuota").value,
    description: document.getElementById("classDescription").value,
  };

  try {
    const res = await fetch("/api/classes", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (res.ok) {
      showToast(data.message, "success");
      closeModal("modalCreateClass");
      loadClasses();
      loadKpiData();
    } else {
      showToast(data.message, "error");
    }
  } catch (err) {
    showToast("Kesalahan server", "error");
  }
}

async function enrollClass(classId) {
  if (!currentUser) {
    openAuthModal('login');
    showToast("Silakan masuk terlebih dahulu untuk mendaftar kelas.", "warning");
    return;
  }
  try {
    const res = await fetch("/api/classes/enroll", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ class_id: classId })
    });
    const data = await res.json();
    if (res.ok) {
      showToast(data.message, "success");
      loadClasses();
      loadKpiData();
    } else {
      showToast(data.message, "error");
    }
  } catch (e) {
    showToast("Gagal mendaftar kelas", "error");
  }
}

// Incubation
async function loadIncubation() {
  if (!currentUser) {
    document.getElementById("incubationList").innerHTML = `
      <div class="card" style="text-align: center; padding: 30px;">
        <p style="color: var(--text-muted); margin-bottom: 12px;">Silakan masuk ke akun alumni Anda untuk melihat atau mengajukan tenant inkubator bisnis.</p>
        <button class="btn btn-primary btn-sm" onclick="openAuthModal('login')">Masuk Sekarang</button>
      </div>
    `;
    return;
  }

  try {
    const res = await fetch("/api/incubation");
    const data = await res.json();
    renderIncubationList(data.tenants || []);
  } catch (e) {
    console.error(e);
  }
}

function renderIncubationList(list) {
  const container = document.getElementById("incubationList");
  if (!list || list.length === 0) {
    container.innerHTML = `<div class="card" style="text-align: center; color: var(--text-muted);">Belum ada pengajuan tenant inkubasi.</div>`;
    return;
  }

  container.innerHTML = list.map(t => `
    <div class="card" style="margin-bottom: 16px;">
      <div class="card-header">
        <div>
          <strong style="font-size: 1.05rem; color: var(--primary);">${t.business_name || t.business_idea.slice(0, 45) + '...'}</strong>
          <span style="font-size: 0.8rem; color: var(--text-muted); margin-left: 8px;">Founder: ${t.founder_name}</span>
        </div>
        <span class="badge ${t.status === 'accepted' ? 'badge-success' : (t.status === 'rejected' ? 'badge-danger' : 'badge-warning')}">
          ${t.status.toUpperCase()}
        </span>
      </div>
      <p style="font-size: 0.85rem; color: var(--text-main); margin-bottom: 6px;"><strong>Deskripsi Usaha / Ide:</strong> ${t.business_idea}</p>
      <p style="font-size: 0.82rem; color: var(--text-muted); margin-bottom: 6px;">Tahap: <strong>${t.stage.toUpperCase()}</strong> • Mentor Penugasan: <strong>${t.mentor_name || "Belum ditugaskan"}</strong></p>
      <p style="font-size: 0.82rem; color: var(--text-muted); margin-bottom: 12px;">Kebutuhan Khusus: ${t.need_desc || "-"}</p>
      <div style="display: flex; gap: 8px; border-top: 1px solid var(--border); padding-top: 10px;">
        <button class="btn btn-primary btn-sm" onclick="openJournalsModal(${t.id}, '${escapeHtml(t.business_name || 'Tenant')}')">Buka Jurnal Pendampingan</button>
        ${currentUser && currentUser.role === 'admin' ? `
          <button class="btn btn-outline-primary btn-sm" onclick="adminReviewTenantPrompt(${t.id})">Review &amp; Mentor</button>
        ` : ''}
      </div>
    </div>
  `).join("");
}

async function openIncubationApplyModal() {
  if (!currentUser) {
    openAuthModal('login');
    showToast("Silakan masuk untuk mendaftar inkubasi.", "warning");
    return;
  }
  // Populate owned businesses
  try {
    const res = await fetch("/api/businesses");
    const data = await res.json();
    const sel = document.getElementById("incubationBizId");
    sel.innerHTML = `<option value="">-- Usaha Baru / Belum Terdaftar --</option>` +
      (data.businesses || []).map(b => `<option value="${b.id}">${b.name}</option>`).join("");
    openModal("modalIncubationApply");
  } catch (e) {
    openModal("modalIncubationApply");
  }
}

async function submitIncubationApply(e) {
  e.preventDefault();
  const payload = {
    business_id: document.getElementById("incubationBizId").value || null,
    business_idea: document.getElementById("incubationIdea").value,
    stage: document.getElementById("incubationStage").value,
    need_desc: document.getElementById("incubationNeed").value,
  };

  try {
    const res = await fetch("/api/incubation/apply", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (res.ok) {
      showToast(data.message, "success");
      closeModal("modalIncubationApply");
      loadIncubation();
      loadKpiData();
    } else {
      showToast(data.message, "error");
    }
  } catch (err) {
    showToast("Kesalahan server", "error");
  }
}

// Journals
async function openJournalsModal(tenantId, tenantName) {
  document.getElementById("journalTenantId").value = tenantId;
  document.getElementById("journalModalTitle").innerText = `Jurnal Pendampingan: ${tenantName}`;
  openModal("modalJournals");
  loadJournals(tenantId);
}

async function loadJournals(tenantId) {
  try {
    const res = await fetch(`/api/incubation/journals?tenant_id=${tenantId}`);
    const data = await res.json();
    const container = document.getElementById("journalEntries");
    if (!data.journals || data.journals.length === 0) {
      container.innerHTML = `<p style="font-size: 0.85rem; color: var(--text-muted); text-align: center;">Belum ada catatan jurnal pada tenant ini.</p>`;
      return;
    }
    container.innerHTML = data.journals.map(j => `
      <div style="background: #ffffff; border: 1px solid var(--border); padding: 12px; border-radius: var(--radius-sm);">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
          <strong style="font-size: 0.85rem; color: var(--primary);">${j.author_name} (${j.author_role})</strong>
          <span class="badge ${j.note_type === 'mentor_feedback' ? 'badge-warning' : 'badge-info'}">${j.note_type}</span>
        </div>
        <p style="font-size: 0.85rem; color: var(--text-main); margin-bottom: 4px;">${j.notes}</p>
        <span style="font-size: 0.72rem; color: var(--text-muted);">${j.created_at}</span>
      </div>
    `).join("");
  } catch (e) {
    console.error(e);
  }
}

async function submitAddJournal(e) {
  e.preventDefault();
  const tenantId = document.getElementById("journalTenantId").value;
  const noteType = document.getElementById("journalNoteType").value;
  const notes = document.getElementById("journalNotes").value;

  try {
    const res = await fetch("/api/incubation/journal", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tenant_id: tenantId, note_type: noteType, notes })
    });
    const data = await res.json();
    if (res.ok) {
      showToast(data.message, "success");
      document.getElementById("journalNotes").value = "";
      loadJournals(tenantId);
    }
  } catch (err) {
    showToast("Gagal menambah catatan jurnal", "error");
  }
}

async function adminReviewTenantPrompt(tenantId) {
  const status = prompt("Masukkan status tenant (accepted / under_review / rejected):", "accepted");
  if (!status) return;
  const mentorId = prompt("ID Mentor yang ditugaskan (kosongkan jika belum ada):", "1");
  try {
    const res = await fetch("/api/incubation/review", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tenant_id: tenantId, status, mentor_id: mentorId ? parseInt(mentorId) : null })
    });
    const data = await res.json();
    showToast(data.message, "success");
    loadIncubation();
    loadKpiData();
  } catch (e) {
    showToast("Gagal review tenant", "error");
  }
}

// Leads
async function loadLeads() {
  if (!currentUser) {
    document.getElementById("leadsList").innerHTML = `
      <div class="card" style="text-align: center; padding: 30px;">
        <p style="color: var(--text-muted); margin-bottom: 12px;">Masuk ke akun Anda untuk melihat atau mengirimkan business lead kemitraan.</p>
        <button class="btn btn-primary btn-sm" onclick="openAuthModal('login')">Masuk</button>
      </div>
    `;
    return;
  }

  try {
    const res = await fetch("/api/leads");
    const data = await res.json();
    renderLeadsList(data.leads || []);
  } catch (e) {
    console.error(e);
  }
}

function renderLeadsList(list) {
  const container = document.getElementById("leadsList");
  if (!list || list.length === 0) {
    container.innerHTML = `<div class="card" style="text-align: center; color: var(--text-muted);">Belum ada peluang bisnis (lead) yang tercatat.</div>`;
    return;
  }
  container.innerHTML = list.map(l => `
    <div class="card" style="margin-bottom: 14px;">
      <div class="card-header">
        <div>
          <strong style="font-size: 1.05rem; color: var(--primary);">${l.title}</strong>
          <p style="font-size: 0.8rem; color: var(--text-muted);">Tujuan: ${l.business_name} • Pengirim: ${l.sender_name}</p>
        </div>
        <span class="badge ${l.status === 'deal' ? 'badge-success' : (l.status === 'declined' ? 'badge-danger' : 'badge-info')}">
          ${l.status.toUpperCase()}
        </span>
      </div>
      <p style="font-size: 0.85rem; color: var(--text-main); margin-bottom: 12px;">${l.message}</p>
      <div style="display: flex; gap: 8px; justify-content: space-between; align-items: center; border-top: 1px solid var(--border); padding-top: 10px;">
        <button class="btn btn-primary btn-sm" onclick="openChatLeadModal(${l.id}, '${escapeHtml(l.title)}')">Buka Ruang Obrolan / Pesan</button>
        <div style="display: flex; gap: 6px;">
          <button class="btn btn-light btn-sm" onclick="updateLeadStatus(${l.id}, 'deal')">Tandai Deal</button>
          <button class="btn btn-light btn-sm" onclick="updateLeadStatus(${l.id}, 'declined')">Tolak</button>
        </div>
      </div>
    </div>
  `).join("");
}

function openSendLeadModal(businessId, businessName) {
  if (!currentUser) {
    openAuthModal('login');
    showToast("Silakan masuk terlebih dahulu untuk mengirimkan penawaran bisnis.", "warning");
    return;
  }
  document.getElementById("leadTargetBizId").value = businessId;
  document.getElementById("leadTargetBizName").value = businessName;
  openModal("modalSendLead");
}

async function submitSendLead(e) {
  e.preventDefault();
  const payload = {
    business_id: document.getElementById("leadTargetBizId").value,
    title: document.getElementById("leadTitle").value,
    message: document.getElementById("leadMessage").value,
  };

  try {
    const res = await fetch("/api/leads", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (res.ok) {
      showToast(data.message, "success");
      closeModal("modalSendLead");
      switchTab("leads");
    } else {
      showToast(data.message, "error");
    }
  } catch (err) {
    showToast("Kesalahan server", "error");
  }
}

async function updateLeadStatus(leadId, status) {
  try {
    const res = await fetch("/api/leads/status", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ lead_id: leadId, status })
    });
    const data = await res.json();
    showToast(data.message, "success");
    loadLeads();
  } catch (e) {
    showToast("Gagal memperbarui status lead", "error");
  }
}

// Chat Lead
async function openChatLeadModal(leadId, title) {
  document.getElementById("chatLeadId").value = leadId;
  document.getElementById("chatLeadTitle").innerText = `Chat: ${title}`;
  openModal("modalChatLead");
  loadChatMessages(leadId);
}

async function loadChatMessages(leadId) {
  try {
    const res = await fetch(`/api/leads/messages?lead_id=${leadId}`);
    const data = await res.json();
    const area = document.getElementById("chatMessagesArea");
    if (!data.messages || data.messages.length === 0) {
      area.innerHTML = `<p style="font-size: 0.85rem; color: var(--text-muted); text-align: center;">Belum ada riwayat pesan.</p>`;
      return;
    }
    area.innerHTML = data.messages.map(m => {
      const isMine = currentUser && m.sender_name === currentUser.full_name;
      return `
        <div class="chat-bubble ${isMine ? 'mine' : 'theirs'}">
          <strong style="font-size: 0.75rem; display: block; margin-bottom: 2px;">${m.sender_name}</strong>
          <span>${m.message}</span>
          <div class="chat-meta">${m.created_at}</div>
        </div>
      `;
    }).join("");
    area.scrollTop = area.scrollHeight;
  } catch (e) {
    console.error(e);
  }
}

async function submitSendChatMessage(e) {
  e.preventDefault();
  const leadId = document.getElementById("chatLeadId").value;
  const input = document.getElementById("chatInputText");
  const msg = input.value.trim();
  if (!msg) return;

  try {
    const res = await fetch("/api/leads/messages", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ lead_id: leadId, message: msg })
    });
    if (res.ok) {
      input.value = "";
      loadChatMessages(leadId);
    }
  } catch (err) {
    showToast("Gagal mengirim pesan", "error");
  }
}

// PKS Agreements
async function loadPks() {
  try {
    const res = await fetch("/api/pks");
    const data = await res.json();
    renderPksTable(data.agreements || []);
  } catch (e) {
    console.error(e);
  }
}

function renderPksTable(list) {
  const tbody = document.getElementById("pksTableBody");
  if (!list || list.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 20px;">Belum ada dokumen PKS yang tersedia.</td></tr>`;
    return;
  }

  tbody.innerHTML = list.map(p => {
    const isProposer = currentUser && currentUser.id === p.proposer_id;
    const isPartner = currentUser && currentUser.id === p.partner_id;
    const isAdmin = currentUser && currentUser.role === "admin";

    return `
      <tr>
        <td>
          <strong>${p.title}</strong><br>
          <span style="font-size: 0.75rem; color: var(--text-muted);">${p.scope}</span>
        </td>
        <td>${p.proposer_name}</td>
        <td>${p.partner_name}</td>
        <td style="font-size: 0.8rem;">${p.start_date || "-"} s/d ${p.end_date || "-"}</td>
        <td>
          <span class="badge ${p.status === 'finalized' ? 'badge-success' : (p.status === 'partner_agreed' ? 'badge-warning' : 'badge-neutral')}">
            ${p.status.toUpperCase()}
          </span>
        </td>
        <td style="font-size: 0.8rem;">${p.final_doc_ref || '<span style="color:var(--text-muted);">-</span>'}</td>
        <td>
          <div style="display: flex; gap: 6px;">
            <button class="btn btn-light btn-sm" onclick="openViewPksModal(${p.id})">Lihat &amp; Cetak</button>
            ${isPartner && p.status === 'draft' ? `
              <button class="btn btn-secondary btn-sm" onclick="agreePks(${p.id})">Setujui Draf</button>
            ` : ''}
            ${isAdmin && (p.status === 'partner_agreed' || p.status === 'draft') ? `
              <button class="btn btn-primary btn-sm" onclick="adminReviewPksPrompt(${p.id})">Review &amp; Finalisasi</button>
            ` : ''}
          </div>
        </td>
      </tr>
    `;
  }).join("");
}

async function openPksModal() {
  if (!currentUser) {
    openAuthModal('login');
    showToast("Silakan masuk terlebih dahulu untuk menyusun draf PKS.", "warning");
    return;
  }
  // Load alumni list for partners
  try {
    const res = await fetch("/api/alumni");
    const data = await res.json();
    const sel = document.getElementById("pksPartnerId");
    sel.innerHTML = (data.alumni || [])
      .filter(a => a.id !== currentUser.id)
      .map(a => `<option value="${a.id}">${a.full_name} (${a.profession || 'Alumni'} - ${a.city || 'Indonesia'})</option>`)
      .join("");
    openModal("modalPks");
  } catch (e) {
    console.error(e);
  }
}

async function submitPksDraft(e) {
  e.preventDefault();
  const payload = {
    partner_id: document.getElementById("pksPartnerId").value,
    title: document.getElementById("pksTitle").value,
    scope: document.getElementById("pksScope").value,
    start_date: document.getElementById("pksStartDate").value,
    end_date: document.getElementById("pksEndDate").value,
    content: document.getElementById("pksContent").value,
  };

  try {
    const res = await fetch("/api/pks", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (res.ok) {
      showToast(data.message, "success");
      closeModal("modalPks");
      loadPks();
      loadKpiData();
    } else {
      showToast(data.message, "error");
    }
  } catch (err) {
    showToast("Kesalahan server", "error");
  }
}

async function agreePks(pksId) {
  if (!confirm("Apakah Anda menyetujui draf naskah PKS ini sebagai draf rancangan kerja sama?")) return;
  try {
    const res = await fetch("/api/pks/agree", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pks_id: pksId })
    });
    const data = await res.json();
    showToast(data.message, "success");
    loadPks();
  } catch (e) {
    showToast("Gagal menyetujui PKS", "error");
  }
}

async function openViewPksModal(pksId) {
  try {
    const res = await fetch(`/api/pks/${pksId}`);
    const data = await res.json();
    if (!res.ok) {
      showToast(data.message, "error");
      return;
    }
    const p = data.agreement;
    document.getElementById("printPksDocRef").innerText = `Nomor Arsip / Registrasi: ${p.final_doc_ref || 'DRAF-INTERNAL-' + p.id}`;
    document.getElementById("printPksContent").innerText = p.content;
    document.getElementById("printPksProposer").innerText = `${p.proposer_name}\n(${p.proposer_profession || 'Pihak Pertama'})`;
    document.getElementById("printPksPartner").innerText = `${p.partner_name}\n(${p.partner_profession || 'Pihak Kedua'})`;

    const auditContainer = document.getElementById("pksAuditLogContainer");
    auditContainer.innerHTML = (p.audit_logs || []).map(l => `
      <div>• <strong>${l.action}</strong> oleh ${l.actor_name} (${l.created_at}): ${l.notes || '-'}</div>
    `).join("");

    openModal("modalViewPks");
  } catch (e) {
    console.error(e);
  }
}

async function adminReviewPksPrompt(pksId) {
  const docRef = prompt("Masukkan nomor referensi arsip fisik dokumen final:", `ARSIP-IKA-PKS-2027-0${pksId}`);
  if (!docRef) return;
  const notes = prompt("Catatan review kurasi pengurus:", "Telah ditelaah pengurus IKA bidang Ekonomi & Bisnis.");
  const publicSummary = confirm("Izinkan ringkasan PKS ini ditampilkan di halaman publik?");

  try {
    const res = await fetch("/api/pks/admin-review", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        pks_id: pksId,
        status: "finalized",
        final_doc_ref: docRef,
        admin_notes: notes,
        is_public_summary: publicSummary ? 1 : 0
      })
    });
    const data = await res.json();
    showToast(data.message, "success");
    loadPks();
    loadKpiData();
  } catch (e) {
    showToast("Gagal review PKS", "error");
  }
}

// KPI Dashboard
async function loadKpiData() {
  try {
    const res = await fetch("/api/kpi");
    const data = await res.json();
    renderKpiCards(data.targets_2027, data.actuals);
  } catch (e) {
    console.error(e);
  }

  // If admin, load pending queues
  if (currentUser && currentUser.role === "admin") {
    loadAdminPendingQueues();
  }
}

function renderKpiCards(targets, actuals) {
  const container = document.getElementById("kpiCardsContainer");
  const metrics = [
    { key: "validated_alumni", label: "Alumni Tervalidasi", target: targets.validated_alumni, actual: actuals.validated_alumni },
    { key: "businesses", label: "Unit Usaha Terdaftar", target: targets.businesses, actual: actuals.businesses },
    { key: "catalog_products", label: "Produk/Jasa di Katalog", target: targets.catalog_products, actual: actuals.catalog_products },
    { key: "active_mentors", label: "Mentor Bisnis Aktif", target: targets.active_mentors, actual: actuals.active_mentors },
    { key: "unique_class_participants", label: "Peserta Unik Kelas", target: targets.unique_class_participants, actual: actuals.unique_class_participants },
    { key: "tenants", label: "Tenant Inkubator", target: targets.tenants, actual: actuals.tenants },
    { key: "assisted_businesses", label: "Usaha Didampingi", target: targets.assisted_businesses, actual: actuals.assisted_businesses },
    { key: "realized_pks", label: "PKS Terealisasi", target: targets.realized_pks, actual: actuals.realized_pks },
  ];

  container.innerHTML = metrics.map(m => {
    const pct = Math.min(100, Math.round((m.actual / m.target) * 100));
    return `
      <div class="kpi-card">
        <div class="kpi-label">${m.label}</div>
        <div class="kpi-value">
          ${m.actual}
          <span class="kpi-target">/ ${m.target}</span>
        </div>
        <div class="kpi-progress-bar">
          <div class="kpi-progress-fill" style="width: ${pct}%;"></div>
        </div>
        <div style="font-size: 0.72rem; color: var(--text-muted); margin-top: 6px; text-align: right;">
          Capaian: <strong>${pct}%</strong> dari target 2027
        </div>
      </div>
    `;
  }).join("");
}

async function loadAdminPendingQueues() {
  try {
    const [alumniRes, bizRes, prodRes] = await Promise.all([
      fetch("/api/alumni"),
      fetch("/api/businesses"),
      fetch("/api/products")
    ]);
    const alumniData = await alumniRes.json();
    const bizData = await bizRes.json();
    const prodData = await prodRes.json();

    const pendingAlumni = (alumniData.alumni || []).filter(a => a.status === 'pending');
    document.getElementById("pendingAlumniCount").innerText = pendingAlumni.length;
    document.getElementById("pendingAlumniList").innerHTML = pendingAlumni.length === 0
      ? `<p style="font-size: 0.85rem; color: var(--text-muted); padding: 8px;">Semua alumni telah diverifikasi.</p>`
      : pendingAlumni.map(a => `
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 6px 0; border-bottom: 1px solid var(--border);">
          <span style="font-size: 0.85rem;"><strong>${a.full_name}</strong> (${a.faculty})</span>
          <button class="btn btn-primary btn-sm" onclick="verifyAlumni(${a.id}, 'approved')">Verifikasi</button>
        </div>
      `).join("");

    const pendingBiz = (bizData.businesses || []).filter(b => !b.is_curated);
    const pendingProd = (prodData.products || []).filter(p => !p.is_curated);
    document.getElementById("pendingCurationsCount").innerText = pendingBiz.length + pendingProd.length;

    let queueHtml = "";
    pendingBiz.forEach(b => {
      queueHtml += `
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 6px 0; border-bottom: 1px solid var(--border);">
          <span style="font-size: 0.85rem;">Usaha: <strong>${b.name}</strong></span>
          <button class="btn btn-primary btn-sm" onclick="curateBusiness(${b.id}, 1)">Kurasi</button>
        </div>
      `;
    });
    pendingProd.forEach(p => {
      queueHtml += `
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 6px 0; border-bottom: 1px solid var(--border);">
          <span style="font-size: 0.85rem;">Produk: <strong>${p.name}</strong></span>
          <button class="btn btn-primary btn-sm" onclick="curateProduct(${p.id}, 1)">Kurasi</button>
        </div>
      `;
    });
    if (!queueHtml) queueHtml = `<p style="font-size: 0.85rem; color: var(--text-muted); padding: 8px;">Semua katalog usaha & produk telah terkurasi.</p>`;
    document.getElementById("pendingCurationsList").innerHTML = queueHtml;
  } catch (e) {
    console.error(e);
  }
}

// Data Privacy (PDP)
async function loadPdp() {
  if (!currentUser) {
    document.getElementById("pdpTableBody").innerHTML = `
      <tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 20px;">Silakan masuk ke akun Anda untuk melihat atau mengajukan permohonan data pribadi.</td></tr>
    `;
    return;
  }

  try {
    const res = await fetch("/api/data-requests");
    const data = await res.json();
    renderPdpTable(data.requests || []);
  } catch (e) {
    console.error(e);
  }
}

function renderPdpTable(list) {
  const tbody = document.getElementById("pdpTableBody");
  if (!list || list.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 20px;">Belum ada permohonan hak data pribadi.</td></tr>`;
    return;
  }

  tbody.innerHTML = list.map(r => `
    <tr>
      <td>#${r.id}</td>
      <td><strong>${r.full_name}</strong><br><span style="font-size: 0.75rem; color: var(--text-muted);">${r.email}</span></td>
      <td><span class="badge badge-info">${r.request_type}</span></td>
      <td style="font-size: 0.85rem;">${r.details}</td>
      <td><span class="badge ${r.status === 'processed' ? 'badge-success' : 'badge-warning'}">${r.status}</span></td>
      <td style="font-size: 0.85rem;">${r.admin_response || '-'}</td>
      <td style="font-size: 0.75rem; color: var(--text-muted);">${r.created_at}</td>
    </tr>
  `).join("");
}

function openPdpModal() {
  if (!currentUser) {
    openAuthModal('login');
    showToast("Silakan masuk terlebih dahulu untuk mengajukan permohonan data.", "warning");
    return;
  }
  openModal("modalPdp");
}

async function submitPdpRequest(e) {
  e.preventDefault();
  const payload = {
    request_type: document.getElementById("pdpType").value,
    details: document.getElementById("pdpDetails").value,
  };

  try {
    const res = await fetch("/api/data-requests", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (res.ok) {
      showToast(data.message, "success");
      closeModal("modalPdp");
      loadPdp();
    } else {
      showToast(data.message, "error");
    }
  } catch (err) {
    showToast("Kesalahan server", "error");
  }
}

// Helper functions
function escapeHtml(text) {
  if (!text) return "";
  return text.replace(/'/g, "\\'").replace(/"/g, "&quot;");
}

function cleanPhone(phone) {
  if (!phone) return "";
  let clean = phone.replace(/[^0-9]/g, "");
  if (clean.startsWith("0")) clean = "62" + clean.substring(1);
  return clean;
}
