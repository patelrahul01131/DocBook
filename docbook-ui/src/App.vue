
<script setup>
import {
  Sidebar,
  SidebarItem,
  ScrollArea,
  FrappeUIProvider
} from "frappe-ui";

import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useAuthStore } from "./stores/auth";

const router = useRouter();
const route = useRoute();
const auth = useAuthStore();

// These pages should not display the sidebar or dashboard header.
const isAuthPage = computed(() =>
  ["/login", "/signup"].includes(route.path)
);

const sidebarItems = [
  {
    label: "Home",
    icon: "search",
    path: "/home"
  },
  {
    label: "My Appointments",
    icon: "calendar",
    path: "/my-appointments"
  },
  {
    label: "Doctor Dashboard",
    icon: "user",
    path: "/doctor"
  }
];

const pageTitle = computed(() => {
  const item = sidebarItems.find(
    item => item.path === route.path
  );

  return item?.label || "DocBook";
});

function navigate(path) {
  router.push(path);
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
            <div class="mt-1 space-y-1">
              <SidebarItem
                v-for="item in sidebarItems"
                :key="item.path"
                :icon="item.icon"
                :active="route.path === item.path"
                @click="navigate(item.path)"
              >
                <span class="flex-1 truncate text-sm">
                  {{ item.label }}
                </span>
              </SidebarItem>
            </div>
          </div>
        </ScrollArea>

        <!-- User profile -->
        <div class="flex shrink-0 items-center p-2">
          <div
            class="flex h-8 w-full items-center gap-2 rounded-4 px-1"
          >
            <img
              src="https://api.dicebear.com/9.x/glass/svg?seed=Lumen"
              alt=""
              class="size-6 shrink-0 rounded-4"
            />

            <span class="flex-1 truncate text-sm text-ink-gray-8">
              {{ auth.user?.full_name || "User" }}
            </span>
          </div>
        </div>
      </Sidebar>

      <!-- Main dashboard content -->
      <main class="min-w-0 flex-1 overflow-auto">
        <header class="border-b px-6 py-4">
          <h1 class="text-lg font-semibold text-ink-gray-9">
            {{ pageTitle }}
          </h1>
        </header>

        <div class="p-6">
          <RouterView />
        </div>
      </main>
    </div>
  </FrappeUIProvider>
</template>