<script lang="ts">
    import type { BreakPointBuilder, PredicateBuilder } from "$lib/breakpoint";
    import Select, { Option } from '@smui/select';
    import IconButton from '@smui/icon-button';
    import Textfield from '@smui/textfield';

    export let predicate_builder: PredicateBuilder;
    export let predicate_builder_parent: PredicateBuilder;
    export let breakpoint_builder_parent: BreakPointBuilder;
    export let possible_predicates: PredicateMapping[];

    function add_predicate_builder(): void {
        predicate_builder.add_predicate_builder()
        predicate_builder = predicate_builder
    }

    function remove_predicate_builder(): void {
        if (predicate_builder_parent === predicate_builder) {
            breakpoint_builder_parent.remove_predicate_builder(predicate_builder)
        } else {
            predicate_builder_parent.remove_predicate_builder(predicate_builder)
        }
        breakpoint_builder_parent = breakpoint_builder_parent
    }
</script>

<div style="display: flex; align-items: center; min-height: 10vh;">
    <div style="padding-right: 5px;">
        <IconButton class="material-icons" on:click={remove_predicate_builder}>
            delete
        </IconButton>
    </div>
    <div class="columns margins">
        <div>
            <Select bind:value={predicate_builder.predicate_name} label="Predicate" role="menu">
                {#each possible_predicates as possible_predicate}
                    <Option value={possible_predicate.name} role="menuitem">{possible_predicate.name}</Option>
                {/each}
            </Select>
        </div>
    </div>
    {#if predicate_builder.predicate_kind() == "compound"}
        <div style="padding: 5px 5px 5px 5px">
            <IconButton class="material-icons" on:click={add_predicate_builder}>
                add
            </IconButton>
        </div>
        <div>
            {#each predicate_builder.predicate_builders as sub_predicate_builder}
                <svelte:self 
                    possible_predicates={possible_predicates} 
                    bind:predicate_builder={sub_predicate_builder}
                    bind:predicate_builder_parent={predicate_builder}
                    bind:breakpoint_builder_parent={breakpoint_builder_parent}
                />
            {/each}
        </div>
    {:else if predicate_builder.predicate_kind() == "flat"}
        <div style="padding-left: 10px">
            <div class="columns margins">
                <div>
                    <Textfield bind:value={predicate_builder.predicate_value} label="Value">
                    </Textfield>
                </div>
            </div>
        </div>
    {/if}
</div>

