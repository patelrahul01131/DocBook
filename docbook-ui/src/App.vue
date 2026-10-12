<script setup>
import { FrappeUIProvider } from "frappe-ui";

import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { isStandaloneRoute } from "./router/router";
import { useAuthStore } from "./stores/auth";
import AgentChat from "./portals/patient/agent/AgentChat.vue";

const router = useRouter();
const route = useRoute();
const auth = useAuthStore();

onMounted(async () => {
  await auth.fetchCurrentUser();
});

// Pages that render WITHOUT the portal sidebar (landing + auth).
const isStandalone = computed(() => isStandaloneRoute(route.path));

// Mobile drawer open/close
const mobileOpen = ref(false);
watch(
  () => route.path,
  () => {
    mobileOpen.value = false;
  }
);

// Read role information from authenticated user
const userRoles = computed(() => {
  const user = auth.user;
  if (!user) return [];

  const roles = user.roles ?? auth.roles ?? [];
  const roleNames = Array.isArray(roles)
    ? roles.map((role) => (typeof role === "string" ? role : role?.role))
    : [];

  if (user.role) roleNames.push(user.role);

  return roleNames
    .filter(Boolean)
    .map((role) => role.toLowerCase().trim());
});

const isLoggedIn = computed(() => Boolean(auth.isLoggedIn && auth.user));

const isDoctor = computed(() => userRoles.value.includes("doctor"));
const isPatient = computed(() => userRoles.value.includes("patient"));
const isAdmin = computed(
  () =>
    userRoles.value.includes("system manager") ||
    userRoles.value.includes("administrator")
);

const portalSubtitle = computed(() => {
  if (isAdmin.value) return "Admin Portal";
  if (isDoctor.value) return "Doctor Portal";
  if (isPatient.value) return "Patient Portal";
  return "DocBook Health";
});

// Sidebar menu configuration
const allSidebarItems = [
  // Patient Portal
  {
    label: "Home",
    icon: "lucide-home",
    path: "/home",
    roles: ["patient", "guest"],
  },
  {
    label: "Patient Dashboard",
    icon: "lucide-layout-dashboard",
    path: "/patient-dashboard",
    roles: ["patient"],
  },
  {
    label: "My Appointments",
    icon: "lucide-calendar",
    path: "/my-appointments",
    roles: ["patient"],
  },
  {
    label: "Medical History",
    icon: "lucide-clipboard-list",
    path: "/medical-history",
    roles: ["patient"],
  },
  {
    label: "Prescriptions",
    icon: "lucide-pill",
    path: "/prescriptions",
    roles: ["patient"],
  },
  {
    label: "Medicine Reminders",
    icon: "lucide-bell",
    path: "/medicine-reminders",
    roles: ["patient"],
  },
  {
    label: "Medicine Catalog",
    icon: "lucide-book-open",
    path: "/medicines",
    roles: ["patient", "doctor", "guest"],
  },

  // Doctor Portal
  {
    label: "Doctor Dashboard",
    icon: "lucide-layout-dashboard",
    path: "/doctor",
    roles: ["doctor"],
  },
  {
    label: "Doctor Appointments",
    icon: "lucide-calendar-check",
    path: "/doctor-appointments",
    roles: ["doctor"],
  },
  {
    label: "My Patients",
    icon: "lucide-users",
    path: "/doctor-patients",
    roles: ["doctor"],
  },
];

const sidebarItems = computed(() => {
  if (!isLoggedIn.value) {
    return allSidebarItems.filter((item) => item.roles.includes("guest"));
  }

  if (isAdmin.value) {
    return allSidebarItems;
  }

  return allSidebarItems.filter((item) =>
    item.roles.some((role) => userRoles.value.includes(role))
  );
});

// Inline lucide-style SVG icons so the sidebar renders crisply without
// depending on any icon font / web component being loaded.
const iconPaths = {
  "lucide-home":
    '<path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>',
  "lucide-layout-dashboard":
    '<rect width="7" height="9" x="3" y="3" rx="1"/><rect width="7" height="5" x="14" y="3" rx="1"/><rect width="7" height="9" x="14" y="12" rx="1"/><rect width="7" height="5" x="3" y="16" rx="1"/>',
  "lucide-calendar":
    '<path d="M8 2v4"/><path d="M16 2v4"/><rect width="18" height="18" x="3" y="4" rx="2"/><path d="M3 10h18"/>',
  "lucide-calendar-check":
    '<path d="M8 2v4"/><path d="M16 2v4"/><rect width="18" height="18" x="3" y="4" rx="2"/><path d="M3 10h18"/><path d="m9 16 2 2 4-4"/>',
  "lucide-clipboard-list":
    '<rect width="8" height="4" x="8" y="2" rx="1" ry="1"/><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><path d="M12 11h4"/><path d="M12 16h4"/><path d="M8 11h.01"/><path d="M8 16h.01"/>',
  "lucide-pill":
    '<path d="m10.5 20.5 10-10a4.95 4.95 0 1 0-7-7l-10 10a4.95 4.95 0 1 0 7 7Z"/><path d="m8.5 8.5 7 7"/>',
  "lucide-bell":
    '<path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/>',
  "lucide-book-open":
    '<path d="M12 7v14"/><path d="M3 18a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h5a4 4 0 0 1 4 4 4 4 0 0 1 4-4h5a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1h-6a3 3 0 0 0-3 3 3 3 0 0 0-3-3z"/>',
  "lucide-users":
    '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
  "lucide-log-out":
    '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" x2="9" y1="12" y2="12"/>',
  "lucide-log-in":
    '<path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/><polyline points="10 17 15 12 10 7"/><line x1="15" x2="3" y1="12" y2="12"/>',
  "lucide-x": '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
  "lucide-stethoscope":
    '<path d="M4.8 2.3A.3.3 0 1 0 5 2H4a2 2 0 0 0-2 2v5a6 6 0 0 0 6 6v0a6 6 0 0 0 6-6V4a2 2 0 0 0-2-2h-1a.2.2 0 1 0 .3.3"/><path d="M8 15v1a6 6 0 0 0 6 6v0a6 6 0 0 0 6-6v-4"/><circle cx="20" cy="10" r="2"/>',
  "lucide-shield-check":
    '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/><path d="m9 12 2 2 4-4"/>',
  "lucide-menu":
    '<line x1="4" x2="20" y1="6" y2="6"/><line x1="4" x2="20" y1="12" y2="12"/><line x1="4" x2="20" y1="18" y2="18"/>',
};

function iconSvg(name) {
  const inner = iconPaths[name] || '<circle cx="12" cy="12" r="9"/>';
  return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${inner}</svg>`;
}


function navigate(path) {
  router.push(path);
}

function goToLogin() {
  router.push("/login");
}

async function logoutAndRedirect() {
  try {
    await auth.logout();
  } finally {
    await router.replace("/login");
  }
}
</script>

<template>
  <FrappeUIProvider>
    <!-- LANDING + LOGIN + SIGNUP: standalone page (no sidebar) -->
    <RouterView v-if="isStandalone" />

    <!-- OTHER PAGES: custom dashboard shell -->
    <div v-else class="db-shell">
      <!-- Mobile top bar (visible on small screens) -->
      <div class="db-mobilebar">
        <button
          type="button"
          class="db-hamburger"
          :aria-expanded="mobileOpen"
          aria-label="Toggle navigation"
          @click="mobileOpen = !mobileOpen"
        >
          <span v-html="iconSvg(mobileOpen ? 'lucide-x' : 'lucide-menu')"></span>
        </button>
        <div class="db-mobilebar-title">
          <span class="db-mobilebar-name">DocBook</span>
          <span class="db-mobilebar-sub">{{ portalSubtitle }}</span>
        </div>
      </div>

      <!-- Mobile backdrop -->
      <div
        v-if="mobileOpen"
        class="db-backdrop"
        @click="mobileOpen = false"
      ></div>

      <!-- ================= SIDEBAR ================= -->
      <aside
        class="db-sidebar"
        :class="{ 'db-sidebar--open': mobileOpen }"
      >
        <!-- Brand -->
        <div class="db-side-brand">
          <div class="db-brand-mark">
            <span v-html="iconSvg('lucide-stethoscope')"></span>
          </div>
          <div class="db-brand-text">
            <span class="db-brand-name">DocBook</span>
            <span class="db-brand-sub">{{ portalSubtitle }}</span>
          </div>
          <button
            type="button"
            class="db-side-close"
            aria-label="Close navigation"
            @click="mobileOpen = false"
          >
            <span v-html="iconSvg('lucide-x')"></span>
          </button>
        </div>

        <!-- Navigation -->
        <nav class="db-side-nav">
          <p class="db-nav-label">Menu</p>
          <ul class="db-nav-list">
            <li v-for="item in sidebarItems" :key="item.path">
              <button
                type="button"
                class="db-nav-item"
                :class="{ 'db-nav-item--active': route.path === item.path }"
                @click="navigate(item.path)"
              >
                <span class="db-nav-icon" v-html="iconSvg(item.icon)"></span>
                <span class="db-nav-text">{{ item.label }}</span>
              </button>
            </li>
          </ul>
        </nav>

        <!-- User profile / Auth footer -->
        <div class="db-side-footer">
          <!-- Logged-in user -->
          <div v-if="auth.isLoggedIn && auth.user" class="db-user-card">
            <img
              class="db-user-avatar"
              :src="
                auth.user.user_image ||
                `https://api.dicebear.com/9.x/glass/svg?seed=${encodeURIComponent(auth.user.email || 'User')}`
              "
              alt="User avatar"
            />
            <div class="db-user-meta">
              <p class="db-user-name">
                {{ auth.user.full_name || auth.user.email || "User" }}
              </p>
              <p class="db-user-role">{{ portalSubtitle }}</p>
            </div>
            <button
              type="button"
              class="db-logout"
              title="Log out"
              aria-label="Log out"
              @click="logoutAndRedirect"
            >
              <span v-html="iconSvg('lucide-log-out')"></span>
            </button>
          </div>

          <!-- Guest user -->
          <button v-else type="button" class="db-login-btn" @click="goToLogin">
            <span class="db-login-icon" v-html="iconSvg('lucide-log-in')"></span>
            Log in
          </button>
        </div>
      </aside>

      <!-- Main dashboard content -->
      <main class="db-main">
        <RouterView />
      </main>

      <!-- Floating AI health assistant (patients only) -->
      <AgentChat />
    </div>
  </FrappeUIProvider>
</template>

<style scoped>
/* ============================================================
   DocBook App Shell + Sidebar
   ============================================================ */

.db-shell {
  display: flex;
  min-height: 100vh;
  background:
    radial-gradient(circle at 12% 4%, rgba(13, 148, 136, 0.06), transparent 30%),
    #f4f7fb;
}

.db-main {
  flex: 1;
  min-width: 0;
  overflow-x: hidden;
}

/* ---------- Sidebar ---------- */
.db-sidebar {
  position: sticky;
  top: 0;
  flex-shrink: 0;
  width: 264px;
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #ffffff;
  border-right: 1px solid #e8eef5;
  box-shadow: 4px 0 24px rgba(15, 23, 42, 0.04);
  z-index: 50;
}

/* Brand header */
.db-side-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px 18px;
  border-bottom: 1px solid #eef2f7;
}

.db-brand-mark {
  width: 42px;
  height: 42px;
  border-radius: 13px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  background: linear-gradient(135deg, #0d9488, #0e7490);
  box-shadow: 0 8px 18px rgba(13, 148, 136, 0.3);
}
.db-brand-mark svg {
  width: 22px;
  height: 22px;
}

.db-brand-text {
  display: flex;
  flex-direction: column;
  line-height: 1.15;
  min-width: 0;
  flex: 1;
}
.db-brand-name {
  font-size: 18px;
  font-weight: 800;
  letter-spacing: -0.4px;
  color: #0f172a;
}
.db-brand-sub {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #0d9488;
}

.db-side-close {
  display: none;
  width: 34px;
  height: 34px;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 10px;
  background: #f1f5f9;
  color: #475569;
  cursor: pointer;
}
.db-side-close svg {
  width: 18px;
  height: 18px;
}
.db-side-close:hover {
  background: #e2e8f0;
  color: #0f172a;
}

/* Navigation */
.db-side-nav {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 18px 12px;
}

.db-nav-label {
  margin: 0 0 10px 10px;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: #94a3b8;
}

.db-nav-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.db-nav-item {
  position: relative;
  width: 100%;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 11px 13px;
  border: none;
  border-radius: 12px;
  background: transparent;
  color: #475569;
  font-family: inherit;
  font-size: 14px;
  font-weight: 600;
  text-align: left;
  cursor: pointer;
  transition: background 0.15s, color 0.15s, transform 0.1s;
}
.db-nav-item:hover {
  background: #f1f5f9;
  color: #0f172a;
}
.db-nav-item:active {
  transform: scale(0.98);
}

.db-nav-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  flex-shrink: 0;
  border-radius: 10px;
  background: #f1f5f9;
  color: #64748b;
  transition: background 0.15s, color 0.15s;
}
.db-nav-icon svg {
  width: 18px;
  height: 18px;
}

.db-nav-text {
  flex: 1;
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Active nav item */
.db-nav-item--active {
  background: linear-gradient(100deg, rgba(13, 148, 136, 0.12), rgba(13, 148, 136, 0.04));
  color: #0f766e;
}
.db-nav-item--active .db-nav-icon {
  background: linear-gradient(135deg, #0d9488, #0e7490);
  color: #fff;
  box-shadow: 0 4px 10px rgba(13, 148, 136, 0.3);
}
.db-nav-item--active::before {
  content: "";
  position: absolute;
  left: -12px;
  top: 50%;
  transform: translateY(-50%);
  width: 4px;
  height: 24px;
  border-radius: 0 4px 4px 0;
  background: #0d9488;
}

/* Footer / user card */
.db-side-footer {
  flex-shrink: 0;
  padding: 14px;
  border-top: 1px solid #eef2f7;
}

.db-user-card {
  display: flex;
  align-items: center;
  gap: 11px;
  padding: 10px;
  border-radius: 14px;
  background: #f8fafc;
  border: 1px solid #eef2f7;
}

.db-user-avatar {
  width: 38px;
  height: 38px;
  flex-shrink: 0;
  border-radius: 11px;
  object-fit: cover;
  background: #e2e8f0;
}

.db-user-meta {
  flex: 1;
  min-width: 0;
}
.db-user-name {
  margin: 0;
  font-size: 13px;
  font-weight: 700;
  color: #0f172a;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.db-user-role {
  margin: 1px 0 0;
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.4px;
  color: #0d9488;
}

.db-logout {
  width: 34px;
  height: 34px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 10px;
  background: #fef2f2;
  color: #dc2626;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}
.db-logout svg {
  width: 17px;
  height: 17px;
}
.db-logout:hover {
  background: #fee2e2;
  color: #b91c1c;
}

/* Guest login button */
.db-login-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 9px;
  padding: 11px 16px;
  border: none;
  border-radius: 12px;
  background: linear-gradient(120deg, #0d9488, #0e7490);
  color: #fff;
  font-family: inherit;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  box-shadow: 0 6px 16px rgba(13, 148, 136, 0.28);
  transition: box-shadow 0.15s, transform 0.1s;
}
.db-login-btn:hover {
  box-shadow: 0 8px 22px rgba(13, 148, 136, 0.38);
}
.db-login-btn:active {
  transform: scale(0.98);
}
.db-login-icon {
  display: flex;
  align-items: center;
}
.db-login-icon svg {
  width: 17px;
  height: 17px;
}

/* ---------- Mobile top bar (hidden on desktop) ---------- */
.db-mobilebar {
  display: none;
}

/* ---------- Backdrop ---------- */
.db-backdrop {
  position: fixed;
  inset: 0;
  z-index: 45;
  background: rgba(15, 23, 42, 0.45);
  backdrop-filter: blur(2px);
  animation: db-fade 0.2s ease;
}

@keyframes db-fade {
  from { opacity: 0; }
  to { opacity: 1; }
}

/* ============================================================
   Responsive — sidebar becomes an off-canvas drawer
   ============================================================ */
@media (max-width: 900px) {
  .db-shell {
    flex-direction: column;
    padding-top: 58px;
  }

  .db-mobilebar {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    z-index: 40;
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 11px 14px;
    background: rgba(255, 255, 255, 0.96);
    backdrop-filter: blur(12px);
    border-bottom: 1px solid #e8eef5;
    box-shadow: 0 2px 12px rgba(15, 23, 42, 0.05);
  }

  .db-hamburger {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 40px;
    height: 40px;
    padding: 0;
    border: none;
    border-radius: 11px;
    background: linear-gradient(135deg, #0d9488, #0e7490);
    color: #fff;
    cursor: pointer;
    box-shadow: 0 4px 12px rgba(13, 148, 136, 0.28);
  }
  .db-hamburger svg {
    width: 20px;
    height: 20px;
  }
  .db-hamburger:active {
    transform: scale(0.95);
  }

  .db-mobilebar-title {
    display: flex;
    flex-direction: column;
    line-height: 1.15;
  }
  .db-mobilebar-name {
    font-size: 16px;
    font-weight: 800;
    letter-spacing: -0.3px;
    color: #0f172a;
  }
  .db-mobilebar-sub {
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: #0d9488;
  }

  .db-sidebar {
    position: fixed;
    top: 0;
    bottom: 0;
    left: 0;
    height: 100vh;
    transform: translateX(-100%);
    transition: transform 0.28s cubic-bezier(0.4, 0, 0.2, 1);
    box-shadow: 0 0 48px rgba(15, 23, 42, 0.22);
  }
  .db-sidebar--open {
    transform: translateX(0);
  }

  .db-side-close {
    display: flex;
  }

  .db-main {
    width: 100%;
  }
}
</style>


