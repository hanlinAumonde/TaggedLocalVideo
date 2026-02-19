import { Injectable } from "@angular/core";

@Injectable({
    providedIn: "root",
})
export class PathHistoryService {
    private pathStack1: number[][] = [];
    private pathStack2: number[][] = [];

    private pathElementsMap: Map<number, string> = new Map();
    private pathElementsReverseMap: Map<string, number> = new Map();
    private pathIdCounter: number = 0;
    
    private recordNewPath(path: string[]): number[] {
        const pathIds: number[] = [];
        path.forEach(p => {
            if(!this.pathElementsReverseMap.has(p)) {
                this.pathElementsMap.set(this.pathIdCounter, p);
                this.pathElementsReverseMap.set(p, this.pathIdCounter);
                this.pathIdCounter++;
            }
            pathIds.push(this.pathElementsReverseMap.get(p) as number);
        })
        return pathIds;
    } 

    private getCurrentPath(): string[] | undefined {
        const currentPathId = this.pathStack1[this.pathStack1.length - 1];
        if (currentPathId) {
            return currentPathId.map(id => this.pathElementsMap.get(id) || "");
        }
        return undefined;
    }

    pushNewPath(path: string[]): void {
        this.pathStack2 = [];
        this.pathStack1.push(this.recordNewPath(path));
    }

    pushForwardPath(): string[] | undefined {
        const path = this.pathStack2.pop();
        if (path !== undefined) {
            this.pathStack1.push(path);
        }
        return this.getCurrentPath();
    }

    popHisotryPath(): string[] | undefined {
        const path = this.pathStack1.pop();
        if (path !== undefined) {
            this.pathStack2.push(path);
        }
        return this.getCurrentPath();
    }

    hasHistory(): boolean {
        return this.pathStack1.length > 0;
    }

    hasForward(): boolean {
        return this.pathStack2.length > 0;
    }

    clearAllHistory(): void {
        this.pathStack1 = [];
        this.pathStack2 = [];
    }
}