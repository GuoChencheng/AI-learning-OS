import type { RecordItem } from "../types";
import { asText } from "../utils";
import { StatusBadge } from "./StatusBadge";

export function RecordTable({
  items,
  columns,
  onSelect,
  selectedId
}: {
  items: RecordItem[];
  columns: string[];
  onSelect?: (item: RecordItem) => void;
  selectedId?: string | null;
}) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column}>{column}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr
              key={item.id}
              className={`${onSelect ? "selectable-row" : ""} ${selectedId === item.id ? "selected-row" : ""}`}
              onClick={() => onSelect?.(item)}
            >
              {columns.map((column) => {
                const value = item[column];
                const badgeColumn = /status|position|intensity|level|role|type|importance|confidence/.test(column);
                return <td key={column}>{badgeColumn ? <StatusBadge value={value} /> : asText(value)}</td>;
              })}
            </tr>
          ))}
          {!items.length && (
            <tr>
              <td colSpan={columns.length}>No records yet.</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
