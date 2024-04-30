<script lang="ts">
    import List, { Item, Text } from '@smui/list';
    import Paper, { Title, Content } from '@smui/paper';
    import Checkbox from '@smui/checkbox';
    import FormField from '@smui/form-field';
    import jQuery from 'jquery';
    import { browser } from '$app/environment';
    import type { SvelteComponent } from 'svelte';
    
    type UpdateFunc = (id: number, type: "current" | "imported") => void

    export let events: TracePayload[] = []
    export let imported_events: TracePayload[] = []
    export let display_callback: UpdateFunc 
    export let running = false

    let width = 23
    let height = 79
    let padding = 10
    let title = "Selected Events"
    let stop_if_different = true
    let imported_list: SvelteComponent

    let different: boolean[] = []
    let current_different = 0
    let dummy_events: string[] = []
    let dummy_imported_events: string[] = []

    function update_dummies(): void {
      if (events.length > imported_events.length) {
        var max = events.length
        var real_list = imported_events
        var dummy_list = dummy_imported_events
        var other_dummy_list = dummy_events
      } else if (events.length < imported_events.length) {
        var max = imported_events.length
        var real_list = events
        var dummy_list = dummy_events
        var other_dummy_list = dummy_imported_events
      } else {
        dummy_events = []
        dummy_imported_events = []
        return
      }
      while ((real_list.length + dummy_list.length) < max) {
        dummy_list.push("")
      }
      while ((real_list.length + dummy_list.length) > max) {
        dummy_list.pop()
      }
      while (!(other_dummy_list.length === 0)) other_dummy_list.pop()
      dummy_events = dummy_events
      dummy_imported_events = dummy_imported_events
    }

    function is_different(): void {
      for (var index = current_different; index < events.length; index++) {
        if (imported_events.length <= index) {
          different[index] = false
        } else if (events[index].selected !== imported_events[index].selected) {
          different[index] = true
        } else {
          different[index] = false
        }
      }
      current_different = index
      if (imported_events.length > events.length) {
        for (let i = current_different; i < imported_events.length; i++) different[i] = false
      }
    }

    function prepare_different(): void {
      is_different()
      update_dummies()
    }

    function current_scroll(): void {
      let position = jQuery("#current").scrollTop()
      if (typeof(position) === "number") jQuery("#imported").scrollTop(position);
    }

    function imported_scroll(): void {
      let position = jQuery("#imported").scrollTop()
      if (typeof(position) === "number") jQuery("#current").scrollTop(position);
    }

    if (browser) {
      jQuery("#current").on("scroll", current_scroll)
    }

    $: {
      if (imported_events.length > 0) {
        width = 11.3698
        height = 74
        padding = 2.5
        title = "Selected Events (Current)"
        prepare_different()
      } else {
        width = 23
        height = 79
        padding = 10
        title = "Selected Events"
      }
    }

    $: if(browser && imported_list) jQuery("#imported").on("scroll", imported_scroll)

    $: {
      if (imported_events.length && events.length) {
        current_different = 0
        is_different()
        update_dummies()
      }
    }

    $: {
      if (browser && imported_events.length > 0) {
        if (stop_if_different) {
          fetch("/breakpoints/enableStopIfDifferent")
        } else {
          fetch("/breakpoints/disableStopIfDifferent")
        }
      }
    }
</script>

<div>
  {#if imported_events.length > 0}
    <div style="height: 5vh;">
      <FormField>
        <Checkbox bind:checked={stop_if_different} disabled={running} />
        <span slot="label">Stop if different</span>
      </FormField>
    </div>
  {/if}

  <div style="display: flex; width: 23vw;">

    {#if imported_events.length > 0}
      <div class="paper-container" style="padding-left: 10px; padding-right: {padding}px; width: {width}vw;">
        <Paper elevation={5}>
          <Title style="width: 100%; height: 6vh;">
            Selected Events (Imported)
          </Title>
          <Content 
            id="imported" 
            style="overflow: scroll; width: 100%; height: 
            {height}vh;"
            bind:this={imported_list}
          >
            <List>
              {#each imported_events as event, i}
                <Item
                  on:SMUI:action={() => (display_callback(event.id, "imported"))}
                  disabled={running}
                  selected={different[i]}
                >
                  <Text>#{i}: {event.selected}</Text>
                </Item>
              {/each}
              {#each dummy_imported_events as _}
                <Item disabled={true}>
                  <Text></Text>
                </Item>
              {/each}
            </List>
          </Content>
        </Paper>
      </div>
    {/if}
    
    <div class="paper-container" style="padding-left: {padding}px; padding-right: 10px; width: {width}vw;">
      <Paper elevation={5}>
        <Title style="width: 100%; height: 6vh;">
          {title}
        </Title>
        <Content 
          id="current" 
          style="overflow: scroll; width: 100%; height: 
          {height}vh;" 
        >
          <List>
            {#each events as event, i}
              <Item 
                on:SMUI:action={() => (display_callback(event.id, "current"))} 
                disabled={running}
                selected={different[i]}
              >
                <Text>#{i}: {event.selected}</Text>
              </Item>
            {/each}
            {#each dummy_events as _}
                <Item disabled={true}>
                  <Text></Text>
                </Item>
              {/each}
          </List>
        </Content>
      </Paper>
    </div>
    
  </div>
</div>
