import { expect, test } from "@playwright/test";

test("catalog loads live API data and opens player details", async ({
  page,
  request,
}) => {
  const response = await request.get("/api/v1/players?limit=1");
  expect(response.ok()).toBeTruthy();
  const catalog = await response.json();
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Know the field." }),
  ).toBeVisible();
  await expect(page.getByText("Backend connected")).toBeVisible();
  if (catalog.total === 0) {
    await expect(
      page.getByText("A fresh start for your roster."),
    ).toBeVisible();
  } else {
    const player = catalog.items[0];
    await page.getByRole("button", { name: player.name, exact: true }).click();
    await expect(page.getByRole("dialog")).toContainText(
      player.provider_player_id,
    );
    await page.getByRole("button", { name: "Close player details" }).click();
    await expect(page.getByRole("dialog")).toHaveCount(0);
    const searched = page.waitForResponse((response) =>
      response.url().includes('/api/v1/players?') &&
      new URL(response.url()).searchParams.get('q') === player.name,
    );
    await page
      .getByRole("textbox", { name: "Search players by name" })
      .fill(player.name);
    await searched;
    await expect(
      page.getByRole("button", { name: player.name, exact: true }).first(),
    ).toBeVisible();
  }
  await page.getByRole('button', { name: 'All sports', exact: true }).click();
  const clearSearch = page.getByRole('button', { name: 'Clear search' });
  if (await clearSearch.isVisible()) {
    const cleared = page.waitForResponse((response) =>
      response.url().includes('/api/v1/players?') &&
      new URL(response.url()).searchParams.get('limit') === '20' &&
      !new URL(response.url()).searchParams.has('q'),
    );
    await clearSearch.click();
    await cleared;
  }
  await page.screenshot({
    path: "test-results/catalog-desktop.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(
    page.getByRole("textbox", { name: "Search players by name" }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
  await page.screenshot({
    path: "test-results/catalog-mobile.png",
    fullPage: true,
  });
});
