import { createBrowserRouter } from "react-router";
import Root from "./components/Root";
import Dashboard from "./components/Dashboard";
import Market from "./components/Market";
import Strategy from "./components/Strategy";
import Backtest from "./components/Backtest";
import Portfolio from "./components/Portfolio";
import Orders from "./components/Orders";

export const router = createBrowserRouter([
  {
    path: "/",
    Component: Root,
    children: [
      { index: true, Component: Dashboard },
      { path: "market", Component: Market },
      { path: "strategy", Component: Strategy },
      { path: "backtest", Component: Backtest },
      { path: "portfolio", Component: Portfolio },
      { path: "orders", Component: Orders },
    ],
  },
]);
