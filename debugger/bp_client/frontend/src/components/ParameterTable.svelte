<script lang="ts">
  import DataTable, { Head, Body, Row, Cell } from '@smui/data-table';
  import Paper, { Title, Content } from '@smui/paper';
  import Textfield from '@smui/textfield';
  import Button, { Label } from '@smui/button';

  type ToDisplay = {
    name: string;
    value: string | number | boolean;
    editable: boolean;
    unit: string;
  }

  type Editor = {
    [name: string]: {
      new_value: any;
    };
  }

  export let parameter_id: number = -1;
  export let current_parameters: ParameterInfo[] = [];
  export let imported_parameters: ParameterInfo[] = [];
  export let data_type: "current" | "imported" = "current";
  export let running = false;
  export let display_parameters = true;

  let parameters: ParameterInfo[] = [];
  let max_id = -1;
  let to_display: ToDisplay[] = [];
  let current_editables: ToDisplay[] = [];
  let editors: Editor = {};
  let height = 29.5;

  function set_parameters(): void {
    for (let editor in editors) {
      fetch("/setParameter/" + editor + "/" + editors[editor].new_value.toString())
    }
  }

  $: {
    if (data_type === "current") {
      parameters = current_parameters
    } else {
      parameters = imported_parameters
    }
  }

  $: {
    if (parameter_id >= 0) {
      to_display = [];
      let current = parameters[parameter_id]
      for (let parameter in current) {
        to_display.push(
          {
            name: parameter, 
            value: current[parameter].value, 
            editable: current[parameter].editable,
            unit: current[parameter].unit,
          }
        )    
      }
      to_display = to_display.sort(
        (a: ToDisplay, b: ToDisplay) => {
          if (a.editable === b.editable) {
            return 0
          } else if (a.editable === false && b.editable === true) {
            return -1
          } else {
            return 1
          }
        }
      )
      if (parameter_id > max_id && data_type === "current") {
        max_id = parameter_id
        current_editables = []
        editors = {}
        for (let d of to_display) {
          if (d.editable) {
            editors[d.name] = {new_value: d.value}
            current_editables.push(d)
          }
        }
        editors = editors
        current_editables = current_editables
      }
    }
  }

  $: {
    if (current_editables.length === 0 && to_display.length === 0) {
      display_parameters = false
      height = 9.5
    }
    else {
      display_parameters = true
      height = 29.5
    }
  }

</script>

<div class="paper-container" style="padding-left: 10px; padding-right: 10px; padding-top: 2.5px;">
  <Paper elevation={5}>
    <Title style="width: 55vw; height: 6vh;">
      System Parameters
    </Title>
    <Content style="width: 55vw; height: {height}vh;">
      {#if parameter_id >= 0 }
        <div style="display: flex;">
          
          {#if to_display.length > 0}
            <div style="overflow: scroll; height: 29.5vh; width: 27vw;">
              <DataTable table$aria-label="People list" style="width: 100%;">
                <Head>
                  <Row>
                    <Cell>Parameter</Cell>
                    <Cell style="width: 70%">Value</Cell>
                  </Row>
                </Head>
                <Body>
                    {#each to_display as data_point}
                      <Row>
                        <Cell>{data_point.name}</Cell>
                        <Cell>{data_point.value}{data_point.unit}</Cell>
                      </Row>
                    {/each}
                </Body>
              </DataTable>
            </div>
          {/if}
          
          {#if current_editables.length > 0}
            <div>
              <div style="overflow: scroll; max-height: 24.5vh;; width: 27vw; padding-left: 19.2px;">
                <DataTable table$aria-label="People list" style="width: 100%;">
                  <Head>
                    <Row>
                      <Cell>Edit</Cell>
                      <Cell></Cell>
                      <Cell></Cell>
                    </Row>
                  </Head>
                  <Body>
                    {#each current_editables as data_point}
                      <Row>
                        <Cell>{data_point.name}</Cell>
                        <Cell>{data_point.value}{data_point.unit}</Cell>
                        <Cell>
                          {#if typeof(data_point.value) === "number"}
                            <Textfield bind:value={editors[data_point.name].new_value} type="number" disabled={running}>
                            </Textfield>
                            {data_point.unit}
                          {:else if typeof(data_point.value) === "string"}
                            <Textfield bind:value={editors[data_point.name].new_value} disabled={running}>
                            </Textfield>
                            {data_point.unit}
                          {/if}
                        </Cell>
                      </Row>
                    {/each}
                  </Body>
                </DataTable>
              </div>

              <div style="height: 4vh; width: 27vw; padding-left: 19.2px; padding-top: 9.04px">
                <Button variant="outlined" on:click={set_parameters} disabled={running}>
                  <Label>Apply</Label>
                </Button>
              </div>
            </div>
          {/if}

        </div>
      {/if}
  </Content>
</Paper>
</div>