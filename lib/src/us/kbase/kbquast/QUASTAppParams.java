
package us.kbase.kbquast;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import javax.annotation.Generated;
import com.fasterxml.jackson.annotation.JsonAnyGetter;
import com.fasterxml.jackson.annotation.JsonAnySetter;
import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonPropertyOrder;


/**
 * <p>Original spec-file type: QUASTAppParams</p>
 * <pre>
 * Input for running QUAST as a Narrative application.
 * workspace_name - the name of the workspace where the KBaseReport object will be saved.
 * assemblies - the list of assemblies upon which QUAST will be run.
 * force_glimmer - running '--glimmer' option regardless of assembly object size
 * </pre>
 * 
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
@Generated("com.googlecode.jsonschema2pojo")
@JsonPropertyOrder({
    "workspace_name",
    "assemblies",
    "force_glimmer"
})
public class QUASTAppParams {

    @JsonProperty("workspace_name")
    private java.lang.String workspaceName;
    @JsonProperty("assemblies")
    private List<String> assemblies;
    @JsonProperty("force_glimmer")
    private Long forceGlimmer;
    private Map<java.lang.String, Object> additionalProperties = new HashMap<java.lang.String, Object>();

    @JsonProperty("workspace_name")
    public java.lang.String getWorkspaceName() {
        return workspaceName;
    }

    @JsonProperty("workspace_name")
    public void setWorkspaceName(java.lang.String workspaceName) {
        this.workspaceName = workspaceName;
    }

    public QUASTAppParams withWorkspaceName(java.lang.String workspaceName) {
        this.workspaceName = workspaceName;
        return this;
    }

    @JsonProperty("assemblies")
    public List<String> getAssemblies() {
        return assemblies;
    }

    @JsonProperty("assemblies")
    public void setAssemblies(List<String> assemblies) {
        this.assemblies = assemblies;
    }

    public QUASTAppParams withAssemblies(List<String> assemblies) {
        this.assemblies = assemblies;
        return this;
    }

    @JsonProperty("force_glimmer")
    public Long getForceGlimmer() {
        return forceGlimmer;
    }

    @JsonProperty("force_glimmer")
    public void setForceGlimmer(Long forceGlimmer) {
        this.forceGlimmer = forceGlimmer;
    }

    public QUASTAppParams withForceGlimmer(Long forceGlimmer) {
        this.forceGlimmer = forceGlimmer;
        return this;
    }

    @JsonAnyGetter
    public Map<java.lang.String, Object> getAdditionalProperties() {
        return this.additionalProperties;
    }

    @JsonAnySetter
    public void setAdditionalProperties(java.lang.String name, Object value) {
        this.additionalProperties.put(name, value);
    }

    @Override
    public java.lang.String toString() {
        return ((((((((("QUASTAppParams"+" [workspaceName=")+ workspaceName)+", assemblies=")+ assemblies)+", forceGlimmer=")+ forceGlimmer)+", additionalProperties=")+ additionalProperties)+"]");
    }

}
