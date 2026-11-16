export const euro = new Intl.NumberFormat("es-ES", {
  style: "currency",
  currency: "EUR",
});
export const dateTime = new Intl.DateTimeFormat("es-ES", {
  dateStyle: "medium",
  timeStyle: "short",
});
export const months = [
  "Ene",
  "Feb",
  "Mar",
  "Abr",
  "May",
  "Jun",
  "Jul",
  "Ago",
  "Sep",
  "Oct",
  "Nov",
  "Dic",
];
export const formatMoney = (value: string) => euro.format(Number(value));
export const formatQuantity = (value: string) =>
  new Intl.NumberFormat("es-ES", { maximumFractionDigits: 3 }).format(
    Number(value),
  );
export const formatPercent = (value: string) =>
  `${new Intl.NumberFormat("es-ES", { maximumFractionDigits: 2 }).format(Number(value))} %`;
export const formatDate = (value: string | null) =>
  value ? dateTime.format(new Date(value)) : "Todavía no disponible";
export const formatMonth = (value: string) =>
  new Intl.DateTimeFormat("es-ES", { month: "short", year: "2-digit" }).format(
    new Date(`${value}-01T12:00:00`),
  );
