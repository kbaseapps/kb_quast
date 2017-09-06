
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
 * <p>Original spec-file type: QUASTParams</p>
 * <pre>
 * Input for running QUAST.
 * assemblies - the list of assemblies upon which QUAST will be run.
 * -OR-
 * files - the list of FASTA files upon which QUAST will be run.
 * Optional arguments:
 * make_handle - create a handle for the new shock node for the report.
 * force_glimmer - running '--glimmer' option regardless of file/assembly object size
 * </pre>
 * 
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
@Generated("com.googlecode.jsonschema2pojo")
@JsonPropertyOrder({
    "assemblies",
    "files",
    "make_handle",
    "force_glimmer"
})
public class QUASTParams {

    @JsonProperty("assemblies")
    private List<String> assemblies;
    @JsonProperty("files")
    private List<FASTAFile> files;
    @JsonProperty("make_handle")
    private Long makeHandle;
    @JsonProperty("force_glimmer")
    private Long forceGlimmer;
    private Map<java.lang.String, Object> additionalProperties = new HashMap<java.lang.String, Object>();

    @JsonProperty("assemblies")
    public List<String> getAssemblies() {
        return assemblies;
    }

    @JsonProperty("assemblies")
    public void setAssemblies(List<String> assemblies) {
        this.assemblies = assemblies;
    }

    public QUASTParams withAssemblies(List<String> assemblies) {
        this.assemblies = assemblies;
        return this;
    }

    @JsonProperty("files")
    public List<FASTAFile> getFiles() {
        return files;
    }

    @JsonProperty("files")
    public void setFiles(List<FASTAFile> files) {
        this.files = files;
    }

    public QUASTParams withFiles(List<FASTAFile> files) {
        this.files = files;
        return this;
    }

    @JsonProperty("make_handle")
    public Long getMakeHandle() {
        return makeHandle;
    }

    @JsonProperty("make_handle")
    public void setMakeHandle(Long makeHandle) {
        this.makeHandle = makeHandle;
    }

    public QUASTParams withMakeHandle(Long makeHandle) {
        this.makeHandle = makeHandle;
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

    public QUASTParams withForceGlimmer(Long forceGlimmer) {
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
        return ((((((((((("QUASTParams"+" [assemblies=")+ assemblies)+", files=")+ files)+", makeHandle=")+ makeHandle)+", forceGlimmer=")+ forceGlimmer)+", additionalProperties=")+ additionalProperties)+"]");
    }

}
