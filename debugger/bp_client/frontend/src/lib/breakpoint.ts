import {v4} from 'uuid';


abstract class Predicate {
    protected _name: string;
    padding: string = "";

    constructor(name: string) {
        this._name = name;
    }

    get name(): string {
        return this._name
    }

    abstract display(): string;

    abstract to_json(): JSONPredicate;
}

export class CompoundPredicate extends Predicate {
    private _predicates: Predicate[]

    constructor(name: string, predicates: Predicate[]) {
        super(name);
        this._predicates = predicates;
    }

    get predicates(): Predicate[] {
        return this._predicates
    }

    display(): string {
        let result = this.padding + this._name + "(\n"
        for (let predicate of this._predicates) {
            predicate.padding = this.padding + "  "
            result += predicate.display() + "\n";
        }
        result += this.padding + ")";
        return result
    }

    to_json(): JSONPredicate {
        let json_sub_precicates = []
        for (let predicate of this._predicates) {
            json_sub_precicates.push(predicate.to_json())
        }
        return {
            "name": this._name,
            "kind": "compound",
            "value": "",
            "predicates": json_sub_precicates,
        }
    }
}

export class FlatPredicate extends Predicate {
    private _content: string

    constructor(name: string, content: string) {
        super(name);
        this._content = content
    }

    get content(): string {
        return this._content
    }

    display(): string {
        return this.padding + this._name + "(" + this._content + ")"
    }

    to_json(): JSONPredicate {
        return {
            "name": this._name,
            "kind": "flat",
            "value": this._content,
            "predicates": [],
        }
    }
}

export class PredicateBuilder {
    private _possible_predicates: PredicateMapping[]
    private _predicate_builders: PredicateBuilder[] = []

    private _predicate_name: string = ""
    private _predicate_value: string = ""

    constructor(possible_predicates: PredicateMapping[]) {
        this._possible_predicates = possible_predicates
    }

    get predicate_builders(): PredicateBuilder[] {
        return this._predicate_builders
    }

    get predicate_name(): string {
        return this._predicate_name
    }

    get predicate_value(): string {
        return this._predicate_value
    }

    set predicate_name(name: string) {
        this._predicate_name = name
    }

    set predicate_value(value: string) {
        this._predicate_value = value
    }

    predicate_kind(): string {
        let filtered = this._possible_predicates.filter((predicate) => predicate.name == this._predicate_name)
        if (filtered.length === 0) {
            return ""
        } else {
            return filtered[0].kind
        }
    }

    add_predicate_builder() {
        this._predicate_builders.push(new PredicateBuilder(this._possible_predicates))
    }

    remove_predicate_builder(predicate_builder: PredicateBuilder): boolean {
        let index = this._predicate_builders.indexOf(predicate_builder)
        if (index === -1) {
            return false
        }
        this._predicate_builders.splice(index, 1)
        return true
    }

    fill_from_predicate(predicate: Predicate): void {
        this._predicate_name = predicate.name
        if (predicate instanceof CompoundPredicate) {
            for (let sub_predicate of predicate.predicates) {
                let sub_builder = new PredicateBuilder(this._possible_predicates)
                sub_builder.fill_from_predicate(sub_predicate)
                this._predicate_builders.push(sub_builder)
            }
        } else if (predicate instanceof FlatPredicate) {
            this._predicate_value = predicate.content
        }
    }

    build(): Predicate {
        if (this.predicate_kind() === "compound") {
            let built_sub_predicates: Predicate[] = []
            for (var sub_predicate_builder of this._predicate_builders) {
                built_sub_predicates.push(sub_predicate_builder.build())
            }
            return new CompoundPredicate(this._predicate_name, built_sub_predicates)
        } else {
            return new FlatPredicate(this._predicate_name, this.predicate_value)
        }
    }

}

export class BreakPoint {
    private _predicates_chain: Predicate[]
    private _id: string
    private _paused: boolean
    private _color: string = "secondary"

    constructor(id: string, chain: Predicate[], paused: boolean = false) {
        this._predicates_chain = chain
        this._id = id
        this._paused = paused
    }

    get predicates_chain(): Predicate[] {
        return this._predicates_chain
    }

    get id(): string {
        return this._id
    }

    get color(): string {
        return this._color
    }

    set fired(fired: boolean) {
        if (fired) this._color = "primary"
        else this._color = "secondary"
    }

    pause(): void {
        this._paused = true
    }

    unpause(): void {
        this._paused = false
    }

    is_paused(): boolean {
        return this._paused
    }

    display(): string {
        let result = ""
        for (let i = 0; i < this._predicates_chain.length; i++) {
            result += this._predicates_chain[i].display();
            if (!(i === this._predicates_chain.length - 1)) {
                result += "\n\n"
            }
        }
        return result
    }

    to_json(): JSONBreakpoint {
        let json_breakpoint: JSONBreakpoint = {
            "id": this._id,
            "chain": [],
            "paused": this._paused,
        }
        for (let predicate of this._predicates_chain) {
            json_breakpoint.chain.push(predicate.to_json())
        }
        return json_breakpoint
    }
}

export class BreakPointBuilder {
    private _predicate_builders: PredicateBuilder[] = []
    private _possible_predicates: PredicateMapping[]

    constructor(possible_predicates: PredicateMapping[]) {
        this._possible_predicates = possible_predicates
    }

    fill_from_breakpoint(breakpoint: BreakPoint) {
        for (let predicate of breakpoint.predicates_chain) {
            let predicate_builder = this.add_predicate_builder()
            predicate_builder.fill_from_predicate(predicate)
        }
    }

    get predicate_builders(): PredicateBuilder[] {
        return this._predicate_builders
    }

    add_predicate_builder(): PredicateBuilder {
        let builder = new PredicateBuilder(this._possible_predicates)
        this._predicate_builders.push(builder)
        return builder
    }

    remove_predicate_builder(predicate_builder: PredicateBuilder): boolean {
        let index = this._predicate_builders.indexOf(predicate_builder)
        if (index === -1) {
            return false
        }
        this._predicate_builders.splice(index, 1)
        return true
    }

    build(): BreakPoint {
        let built_predicates: Predicate[] = []
        for (var predicate_builder of this._predicate_builders) {
            built_predicates.push(predicate_builder.build())
        }
        return new BreakPoint(v4(), built_predicates)
    }
}

function predicate_from_json(json_predicate: JSONPredicate): Predicate {
    if (json_predicate.kind == "compound") {
        let predicates: Predicate[] = []
        for (let sub_json_predicate of json_predicate.predicates) {
            predicates.push(predicate_from_json(sub_json_predicate))
        }
        return new CompoundPredicate(json_predicate.name, predicates)
    } else {
        return new FlatPredicate(json_predicate.name, json_predicate.value)
    }
}

export function breakpoint_from_json(json_breakpoint: JSONBreakpoint): BreakPoint {
    let predicates: Predicate[] = []
    for (let json_predicate of json_breakpoint.chain) {
        predicates.push(predicate_from_json(json_predicate))
    }
    return new BreakPoint(json_breakpoint.id, predicates, json_breakpoint.paused)
}
