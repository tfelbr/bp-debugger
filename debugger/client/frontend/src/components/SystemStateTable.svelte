<script lang="ts">
  import DataTable, { Head, Body, Row, Cell } from '@smui/data-table';
  import Paper, { Title, Content } from '@smui/paper';

  type ToDisplay = {
    event: string;
    requested_by: string[];
    blocked_by: string[];
    waited_for_by: string[];
    request_priorities: number[];
  }

  export let selected: string = "";
  export let event_id: number = -1;
  export let data_type: "current" | "imported" = "current"
  export let parameters_existent: boolean = true

  let to_display: ToDisplay[] = []
  let current: StateInfo[] = []
  let height = 36.9

  async function get_state_info(data_type: string): Promise<void> {
    let state_info: StateInfo[] = await (await fetch("/getStateData/" + data_type + "/" + event_id.toString())).json()
    current = state_info
  }

  function get_max(numbers: number[]): number {
    let current_max = 0
    for (let n of numbers) {
      if (n > current_max) current_max = n
    }
    return current_max
  }

  $: {
    if (parameters_existent) height = 36.9
    else height = 56.9
  }

  $: if (event_id >= 0) {get_state_info(data_type)}

  $: {
    if (current.length > 0) {
      to_display = [];
      let all_events: string[] = [];
      for (let data of current) {
        let all_lists = [data.request, data.block, data.wait_for]
        for (let event_list of all_lists) {
          for (let event of event_list) {
            let index = all_events.indexOf(event)
            if (index === -1 && event !== "ALL") {
              all_events.push(event)
              to_display.push(
                {
                  "event": event,
                  "requested_by": [],
                  "blocked_by": [],
                  "waited_for_by": [],
                  "request_priorities": [],
                }
              )
            }
          }
        }
      }

      for (let data of current) {

        // requested events
        for (let request of data.request) {
          let index = all_events.indexOf(request)
          to_display[index].requested_by.push(data.name + "( " + data.priority.toString() + " )")
          to_display[index].request_priorities.push(data.priority)
        }

        // blocked
        for (let block of data.block) {
          let index = all_events.indexOf(block)
          to_display[index].blocked_by.push(data.name)
        }

        // waited for
        for (let waited_for of data.wait_for) {
          let index = all_events.indexOf(waited_for)
          to_display[index].waited_for_by.push(data.name)
        }
      }

      to_display = to_display
    }
  }

</script>

<div class="paper-container" style="padding-left: 10px; padding-right: 10px; padding-bottom: 2.5px;">
  <Paper elevation={5}>
    <Title style="width: 55vw; height: 6vh;">
      System State
    </Title>
    <Content style="overflow: scroll; width: 55vw; height: {height}vh;">
      {#if event_id >= 0 }
        <DataTable table$aria-label="People list" style="min-width: 100%;">
          <Head>
            <Row>
              <Cell>Event</Cell>
              <Cell>Requested By</Cell>
              <Cell>Blocked By</Cell>
              <Cell>Waited For By</Cell>
              <Cell>Highest Request Priority</Cell>
            </Row>
          </Head>
          <Body>
              {#each to_display as data_point}
                {#if data_point.event == selected}
                  <Row style="background-color: DarkRed;">
                    <Cell><pre style="color: White;">{data_point.event}</pre></Cell>
                    <Cell><pre style="color: White;">{data_point.requested_by.join("\n")}</pre></Cell>
                    <Cell><pre style="color: White;">{data_point.blocked_by.join("\n")}</pre></Cell>
                    <Cell><pre style="color: White;">{data_point.waited_for_by.join("\n")}</pre></Cell>
                    <Cell><pre style="color: White;">{get_max(data_point.request_priorities)}</pre></Cell>
                  </Row>
                {:else if data_point.blocked_by.length == 0 && data_point.requested_by.length > 0}
                  <Row style="background-color: DarkGoldenRod;">
                    <Cell><pre style="color: White;">{data_point.event}</pre></Cell>
                    <Cell><pre style="color: White;">{data_point.requested_by.join("\n")}</pre></Cell>
                    <Cell><pre style="color: White;">{data_point.blocked_by.join("\n")}</pre></Cell>
                    <Cell><pre style="color: White;">{data_point.waited_for_by.join("\n")}</pre></Cell>
                    <Cell><pre style="color: White;">{get_max(data_point.request_priorities)}</pre></Cell>
                  </Row>
                {:else}
                  <Row>
                    <Cell><pre>{data_point.event}</pre></Cell>
                    <Cell><pre>{data_point.requested_by.join("\n")}</pre></Cell>
                    <Cell><pre>{data_point.blocked_by.join("\n")}</pre></Cell>
                    <Cell><pre>{data_point.waited_for_by.join("\n")}</pre></Cell>
                    <Cell><pre>{get_max(data_point.request_priorities)}</pre></Cell>
                  </Row>
                {/if}
              {/each}
          </Body>
        </DataTable>
      {/if}
  </Content>
</Paper>
</div>