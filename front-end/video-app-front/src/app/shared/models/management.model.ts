import { FileBrowseNode } from "./GQL-result.model";

export type SortCriterion = {
    index: number;
    order: boolean; // true for ascending, false for descending
}

export type ManagementRefreshState = {
  scrollPosition: number;
  sortCriteria: SortCriterion;
};

export enum ItemsSortOption {
  NAME_ASC = 'NAME_ASC',
  NAME_DESC = 'NAME_DESC',
  SIZE_ASC = 'SIZE_ASC',
  SIZE_DESC = 'SIZE_DESC',
  DATE_ASC = 'DATE_ASC',
  DATE_DESC = 'DATE_DESC'
}

export function comparatorBySortOption(option: ItemsSortOption) {
    switch(option){
        case ItemsSortOption.NAME_ASC:
            return (a: FileBrowseNode, b: FileBrowseNode) => a.node.name.localeCompare(b.node.name);
        case ItemsSortOption.NAME_DESC:
            return (a: FileBrowseNode, b: FileBrowseNode) => b.node.name.localeCompare(a.node.name);
        case ItemsSortOption.SIZE_ASC:
            return (a: FileBrowseNode, b: FileBrowseNode) => (a.node.size ?? 0) - (b.node.size ?? 0);
        case ItemsSortOption.SIZE_DESC:
            return (a: FileBrowseNode, b: FileBrowseNode) => (b.node.size ?? 0) - (a.node.size ?? 0);
        case ItemsSortOption.DATE_ASC:
            return (a: FileBrowseNode, b: FileBrowseNode) => (a.node.lastModifyTime ?? 0) - (b.node.lastModifyTime ?? 0);
        case ItemsSortOption.DATE_DESC:
            return (a: FileBrowseNode, b: FileBrowseNode) => (b.node.lastModifyTime ?? 0) - (a.node.lastModifyTime ?? 0);
    }
}