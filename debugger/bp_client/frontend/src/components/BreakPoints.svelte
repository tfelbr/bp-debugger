<script lang="ts">
  import Paper, { Title as PTitle, Content as PContent } from '@smui/paper';
  import Accordion, { Panel, Header, Content as AContent } from '@smui-extra/accordion';
  import Fab, { Icon } from '@smui/fab';
  import IconButton from '@smui/icon-button';
  import { BreakPoint, BreakPointBuilder, breakpoint_from_json } from '$lib/breakpoint';
  import Dialog, { Title as DTitle, Content, Actions, Header as DHeader } from '@smui/dialog';
  import Button, { Label } from '@smui/button';
  import PredicateSelect from './PredicateSelect.svelte';
    import { browser } from '$app/environment';
  

  export let running = false;
  export let highlight: string[] = [];

  let breakpoints: BreakPoint[] = [];

  function highlight_breakpoints(): void {
    for (let b of breakpoints) {
      if (highlight.includes(b.id)) b.fired = true
      else b.fired = false
      breakpoints = breakpoints
    }
  }

  $: if (highlight) highlight_breakpoints()

  async function register_json_break_points(): Promise<void> {
    let json_breakpoints: JSONBreakpoint[] = await (await fetch("/breakpoints/get")).json()
    for (let json_breakpoint of json_breakpoints) {
      breakpoints.push(breakpoint_from_json(json_breakpoint))
    }
    breakpoints = breakpoints
  }

  if (browser) register_json_break_points()

  let breakpoint_builders: BreakPointBuilder[] = []

  let dialog_mode = "";
  let dialog_open = false;
  let current_index = -1;
  let possible_predicates: PredicateMapping[] = [
    {
      name: "AND",
      kind: "compound",
    },
    {
      name: "OR",
      kind: "compound",
    },
    {
      name: "EVENT_SELECTED",
      kind: "flat",
    },
    {
      name: "EVENT_REQUESTED",
      kind: "flat",
    },
    {
      name: "EVENT_BLOCKED",
      kind: "flat",
    },
    {
      name: "EVENT_NUMBER",
      kind: "flat",
    },
  ]

  function open_create_dialog(): void {
    current_index = breakpoints.length
    breakpoint_builders[current_index] = new BreakPointBuilder(possible_predicates)
    breakpoint_builders = breakpoint_builders
    dialog_mode = "Create";
    dialog_open = true;
  }

  function open_edit_dialog(index: number): void {
    current_index = index;
    let builder = new BreakPointBuilder(possible_predicates)
    builder.fill_from_breakpoint(breakpoints[index])
    breakpoint_builders[index] = builder
    dialog_mode = "Edit";
    dialog_open = true;
  }

  function add_predicate_builder(): void {
    breakpoint_builders[current_index].add_predicate_builder()
    breakpoint_builders = breakpoint_builders
  }

  function remove_breakpoint(index: number): void {
    let removed_breakpoint = breakpoints.splice(index, 1)[0]
    fetch("/breakpoints/delete/" + removed_breakpoint.id)
    breakpoints = breakpoints
  }

  function pause_breakpoint(breakpoint: BreakPoint): void {
    fetch("/breakpoints/pause/" + breakpoint.id)
    breakpoint.pause()
    breakpoints = breakpoints
  }

  function unpause_breakpoint(breakpoint: BreakPoint): void {
    fetch("/breakpoints/unpause/" + breakpoint.id)
    breakpoint.unpause()
    breakpoints = breakpoints
  }

  function dialog_apply(): void {
    let breakpoint = breakpoint_builders[current_index].build()
    if (dialog_mode == "Edit") {
      let old_breakpoint = breakpoints[current_index]
      fetch("/breakpoints/delete/" + old_breakpoint.id)
    }

    breakpoints[current_index] = breakpoint
    fetch(
      "/breakpoints/add",
      {
        method: "POST",
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(breakpoint.to_json())
      }
    )

    dialog_open = false
    current_index = -1
    breakpoint_builders = []
  }

  function dialog_discard(): void {
    dialog_open = false
    current_index = -1
    breakpoint_builders = []
  }

</script>

<div class="paper-container" style="padding-left: 10px; padding-right: 10px;">
  <Paper elevation={5}>

    <PTitle style="width: 16vw; height: 6vh;">
      Break Points
      <Fab mini style="float: right;" on:click={open_create_dialog} disabled={running}>
        <Icon class="material-icons">add</Icon>
      </Fab>
    </PTitle>
 
    <PContent style="overflow: scroll; width: 16vw; height: 79vh;">
      <div class="accordion-container">
        <Accordion multiple>

          {#each breakpoints as breakpoint, i}
            <Panel color={breakpoint.color}>
              <Header>
                #{i+1}
                <span slot="description">
                  {#if breakpoint.is_paused()}
                    Paused
                  {/if}
                </span> 
              </Header>
              <AContent>
                  <IconButton class="material-icons" on:click={() => open_edit_dialog(i)} disabled={running}>
                    build
                  </IconButton>
                  <IconButton class="material-icons" on:click={() => remove_breakpoint(i)} disabled={running}>
                    delete
                  </IconButton>
                  {#if !breakpoint.is_paused()}
                    <IconButton class="material-icons" on:click={() => pause_breakpoint(breakpoint)}>
                      pause
                    </IconButton>
                  {/if}
                  {#if breakpoint.is_paused()}
                    <IconButton class="material-icons" on:click={() => unpause_breakpoint(breakpoint)}>
                      play_arrow
                    </IconButton>
                  {/if}
                  <div style="overflow: scroll; max-height: 50vh;">
                    <pre>
                      {"\n" + breakpoint.display()}
                    </pre>
                  </div>
              </AContent>
            </Panel>
          {/each}

        </Accordion>
      </div>
    </PContent>
  </Paper>
</div>

<Dialog
  bind:open={dialog_open}
  fullscreen
  aria-labelledby="over-fullscreen-title"
  aria-describedby="over-fullscreen-content"
>
  <!-- Title cannot contain leading whitespace due to mdc-typography-baseline-top() -->
  <DHeader>
    <DTitle id="over-fullscreen-title">{dialog_mode} Breakpoint</DTitle>
  </DHeader>

  <Content id="over-fullscreen-content" style="height: 60vh;">

    {#if current_index >= 0}
      {#each breakpoint_builders[current_index].predicate_builders as predicate_builder}
        <div style="padding-bottom: 10px; padding-top: 10px;">
          <div class="paper-container">
            <Paper elevation={5}>
              <PContent>
                <PredicateSelect
                  possible_predicates={possible_predicates} 
                  bind:predicate_builder={predicate_builder}
                  bind:predicate_builder_parent={predicate_builder}
                  bind:breakpoint_builder_parent={breakpoint_builders[current_index]}
                />
              </PContent>
            </Paper>
          </div>
        </div>
      {/each}
    {/if}
    
    <div style="padding-top: 10px;">
      <Fab mini on:click={add_predicate_builder}>
        <Icon class="material-icons">add</Icon>
      </Fab>
    </div>

  </Content>
  <Actions>
    <Button on:click={dialog_apply}>
      <Label>Apply</Label>
    </Button>
    <Button on:click={dialog_discard}>
      <Label>Discard</Label>
    </Button>
  </Actions>
</Dialog>