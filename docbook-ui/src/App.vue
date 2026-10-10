

<script setup>
import {
  Sidebar,
  SidebarItem,
  ScrollArea,
  FrappeUIProvider,
  Dropdown,
} from "frappe-ui";

import { computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useAuthStore } from "./stores/auth";

const router = useRouter();
const route = useRoute();
const auth = useAuthStore();

onMounted(async () => {
  await auth.fetchCurrentUser();
});

const isAuthPage = computed(() =>
  ["/login", "/signup"].includes(route.path)
);

// Read role information from the authenticated user.
const userRoles = computed(() => {
  const user = auth.user;

  if (!user) return [];

  const roles = user.roles ?? auth.roles ?? [];
  const roleNames = Array.isArray(roles)
    ? roles.map((role) =>
        typeof role === "string" ? role : role?.role
      )
    : [];

  // Also support an app-specific single role field.
  if (user.role) roleNames.push(user.role);

  return roleNames
    .filter(Boolean)
    .map((role) => role.toLowerCase().trim());
});

const isLoggedIn = computed(
  () => Boolean(auth.isLoggedIn && auth.user)
);

const isDoctor = computed(() =>
  userRoles.value.includes("doctor")
);

const isPatient = computed(() =>
  userRoles.value.includes("patient")
);

const isAdmin = computed(
  () =>
    userRoles.value.includes("system manager") ||
    userRoles.value.includes("administrator")
);

// Define which roles can see each sidebar page.
const allSidebarItems = [
  {
    label: "Home",
    icon: "lucide-home",
    path: "/home",
    roles: ["patient"],
  },
  {
    label: "Patient Dashboard",
    icon: "lucide-layout-dashboard",
    path: "/patient-dashboard",
    roles: ["patient"],
  },
  {
    label:"Doctor Profile & Booking",
    icon: "lucide-heart-handshake",
    path: "/doctor-profile-booking",
    roles: ["patient"],
  },
  {
    label: "My Appointments",
    icon: "lucide-calendar",
    path: "/my-appointments",
    roles: ["patient"],
  },
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
];

const sidebarItems = computed(() => {
  if (!isLoggedIn.value) return [];

  if (isAdmin.value) return allSidebarItems;

  return allSidebarItems.filter((item) =>
    item.roles.some((role) => userRoles.value.includes(role))
  );
});

const profileOptions = [
  {
    label: "Logout",
    icon: "lucide-log-out",
    onClick: logoutAndRedirect,
  },
];

const pageTitle = computed(() => {
  const item = sidebarItems.value.find(
    (item) => item.path === route.path
  );

  return item?.label || "DocBook";
});

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
    <!-- LOGIN AND SIGNUP: standalone page -->
    <RouterView v-if="isAuthPage" />

    <!-- OTHER PAGES: normal dashboard layout -->
    <div v-else class="flex h-screen">
      <Sidebar
        :collapsible="false"
        width="14rem"
        class="shrink-0"
      >
        <!-- Sidebar header -->
        <div class="flex shrink-0 items-center p-3">
          <div class="flex items-center gap-2">
            <div
              class="flex size-8 items-center justify-center rounded-lg bg-surface-gray-2"
            >
              🩺
            </div>

            <span class="text-base font-semibold text-ink-gray-8">
              DocBook
            </span>
          </div>
        </div>

        <!-- Navigation -->
        <ScrollArea class="min-h-0 flex-1">
          <div class="px-2 pt-3">
            <div class="mt-1 space-y-3">
              <SidebarItem
                v-for="item in sidebarItems"
                :key="item.path"
                :icon="item.icon"
                :active="route.path === item.path"
                @click="navigate(item.path)"
              >
                <span class="flex-1 truncate text-sm ">
                  {{ item.label }}
                </span>
              </SidebarItem>
            </div>
          </div>
        </ScrollArea>

        <!-- User profile -->

      <div class="shrink-0 border-t border-outline-gray-1 p-2">
        <!-- Logged-in user -->
        <Dropdown
          v-if="auth.isLoggedIn && auth.user"
          :options="profileOptions"
        >
          <template #default="{ open }">
            <button
              type="button"
              class="flex h-10 w-full items-center gap-2 rounded-lg px-2
                    text-left transition hover:bg-surface-gray-2"
              :aria-expanded="open"
            >
              <img
                :src="
                  auth.user.user_image ||
                  `https://api.dicebear.com/9.x/glass/svg?seed=${encodeURIComponent(auth.user.email || 'User')}`
                "
                alt="User avatar"
                class="size-7 shrink-0 rounded-full"
              />

              <span class="flex-1 truncate text-sm text-ink-gray-8">
                {{ auth.user.full_name || auth.user.email || "User" }}
              </span>

              <span class="text-ink-gray-5">
                <svg
                  v-if="!open"
                  class="size-4"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                >
                  <path d="m6 9 6 6 6-6" />
                </svg>
                <svg
                  v-else
                  class="size-4"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                >
                  <path d="m18 15-6-6-6 6" />
                </svg>
              </span>
            </button>
          </template>
        </Dropdown>

        <!-- Guest user -->
        <button
          v-else
          type="button"
          class="flex h-10 w-full items-center justify-center shadow-lg cursor-pointer
                rounded-lg bg-surface-gray-2 text-sm font-medium
                text-ink-gray-8 transition hover:bg-surface-gray-3"
          @click="goToLogin"
        >
          <span class="iconify lucide--log-in size-4"></span>
          Login
        </button>
      </div>

      </Sidebar>

      <!-- Main dashboard content -->
      <main class="min-w-0 flex-1 overflow-auto">
        <!-- <header class="border-b px-6 py-4">
          <h1 class="text-lg font-semibold text-ink-gray-9">
            {{ pageTitle }}
          </h1>
        </header> -->

        <div class="">
          <RouterView />
        </div>
      </main>
    </div>
  </FrappeUIProvider>
</template>