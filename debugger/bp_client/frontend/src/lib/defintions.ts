type ParameterInfo = {
  [name: string]: {
    value: string | number | boolean;
    editable: boolean;
    unit: string;
  }
}

type StateInfo = {
  name: string;
  request: string[];
  wait_for: string[];
  block: string[];
  priority: number;
}

type TracePayload = {
  type: "trace";
  selected: string;
  id: number;
  parameters: ParameterInfo;
}

type InfoPayload = {
  type: "info";
  paused: boolean;
  ended: boolean;
  breakpoint_ids: string[];
}

type InitialPayload = {
  type: "initial";
  timeout: number;
  parameters: ParameterInfo;
  running: boolean;
}

type PredicateMapping = {
  name: string;
  kind: "compound" | "flat";
}

type JSONPredicate = { 
  name: string;
  value: string;
  kind: "compound" | "flat";
  predicates: JSONPredicate[]  
}

type JSONBreakpoint = {
  id: string;
  chain: JSONPredicate[];
  paused: boolean;
}
