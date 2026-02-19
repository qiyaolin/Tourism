import { createRouter, createWebHistory } from "vue-router";

import ExplorePage from "./pages/ExplorePage.vue";
import LoginPage from "./pages/LoginPage.vue";
import MyItinerariesPage from "./pages/MyItinerariesPage.vue";
import PublicItineraryPage from "./pages/PublicItineraryPage.vue";
import EditorWorkbenchPage from "./pages/EditorWorkbenchPage.vue";
import { useAuth } from "./composables/useAuth";

const routes = [
  { path: "/", redirect: "/explore" },
  { path: "/login", component: LoginPage },
  { path: "/explore", component: ExplorePage },
  { path: "/itineraries/:id", component: PublicItineraryPage, props: true },
  { path: "/mine", component: MyItinerariesPage, meta: { requiresAuth: true } },
  { path: "/editor", component: EditorWorkbenchPage, meta: { requiresAuth: true } }
];

const router = createRouter({
  history: createWebHistory(),
  routes
});

router.beforeEach(async (to) => {
  const { isLoggedIn, loadMe } = useAuth();
  if (!to.meta.requiresAuth) {
    return true;
  }
  if (!isLoggedIn.value) {
    return { path: "/login", query: { redirect: to.fullPath } };
  }
  await loadMe();
  if (!isLoggedIn.value) {
    return { path: "/login", query: { redirect: to.fullPath } };
  }
  return true;
});

export default router;
