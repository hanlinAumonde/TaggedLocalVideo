import { Injectable } from "@angular/core";

@Injectable({
    providedIn: "root",
})
export class PathHistoryService {
    private pathStack1: string[][] = [];
    private pathStack2: string[][] = [];

    pushNewPath(path: string[]): void {
        this.pathStack2 = [];
        this.pathStack1.push([...path]);
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

    private getCurrentPath(): string[] | undefined {
        const current = this.pathStack1[this.pathStack1.length - 1];
        return current ? [...current] : undefined;
    }
}
