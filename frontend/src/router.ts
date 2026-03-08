import { createRouter, createWebHistory } from "vue-router";

import ExplorePage from "./pages/ExplorePage.vue";
import CollabJoinPage from "./pages/CollabJoinPage.vue";
import LoginPage from "./pages/LoginPage.vue";
import MyItinerariesPage from "./pages/MyItinerariesPage.vue";
import MyCorrectionsPage from "./pages/MyCorrectionsPage.vue";
import PublicItineraryPage from "./pages/PublicItineraryPage.vue";
import EditorWorkbenchPage from "./pages/EditorWorkbenchPage.vue";
import CorrectionReviewPage from "./pages/CorrectionReviewPage.vue";
import NotificationsPage from "./pages/NotificationsPage.vue";
import PassportPage from "./pages/PassportPage.vue";
import TerritoryPage from "./pages/TerritoryPage.vue";
import AdminTerritoryReviewPage from "./pages/AdminTerritoryReviewPage.vue";
import BountyBoardPage from "./pages/BountyBoardPage.vue";
import AdminBountyReviewPage from "./pages/AdminBountyReviewPage.vue";
import EditorWorkbenchV2 from "./pages/EditorWorkbenchV2.vue";
import { useAuth } from "./composables/useAuth";

const routes = [
  { path: "/", redirect: "/explore" },
  { path: "/login", component: LoginPage },
  { path: "/collab/join", component: CollabJoinPage, meta: { requiresAuth: true } },
  { path: "/explore", component: ExplorePage },
  { path: "/itineraries/:id", component: PublicItineraryPage, props: true },
  { path: "/mine", component: MyItinerariesPage, meta: { requiresAuth: true } },
  { path: "/editor", component: EditorWorkbenchV2, meta: { requiresAuth: true } },
  { path: "/editor/legacy", component: EditorWorkbenchPage, meta: { requiresAuth: true } },
  { path: "/corrections/mine", component: MyCorrectionsPage, meta: { requiresAuth: true } },
  { path: "/corrections/review", component: CorrectionReviewPage, meta: { requiresAuth: true } },
  { path: "/notifications", component: NotificationsPage, meta: { requiresAuth: true } },
  { path: "/passport", component: PassportPage, meta: { requiresAuth: true } },
  { path: "/bounties", component: BountyBoardPage, meta: { requiresAuth: true } },
  { path: "/territories", component: TerritoryPage },
  { path: "/admin/territories/review", component: AdminTerritoryReviewPage, meta: { requiresAuth: true } },
  { path: "/admin/bounties/review", component: AdminBountyReviewPage, meta: { requiresAuth: true } }
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
